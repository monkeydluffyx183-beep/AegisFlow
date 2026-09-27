from __future__ import annotations

import base64
import json
import time
import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware
from scoring.decision import Thresholds
from scoring.engine import ScoringEngine
from scoring.schemas import ScoreRequest as CoreScoreRequest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import settings
from .db import (
    Alert,
    AuditLog,
    Case,
    Decision,
    EvidenceItem,
    SARDraft,
    SessionLocal,
    ThresholdConfig,
    Transaction,
    User,
    audit,
    init_db,
    new_id,
)
from .investigation import _build_graph, run_investigation
from .schemas import ApprovalIn, DispositionIn, EditDraftIn, LoginIn, ScoreRequest, ThresholdsIn, TransactionIn

app = FastAPI(
    title="AegisFlow API",
    version="0.1.0",
    description="Explainable real-time fraud decisions and human-approved AML investigations.",
    docs_url="/docs",
    redoc_url="/redoc",
)
app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins), allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

scorer = ScoringEngine(Thresholds(review=settings.review_threshold, decline=settings.decline_threshold))
metrics: dict[str, int | float] = {"transactions_total": 0, "alerts_total": 0, "cases_total": 0, "approvals_total": 0, "score_latency_ms_sum": 0.0}


def session_scope() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def actor_context(x_user_email: str | None = Header(default=None), x_role: str | None = Header(default=None), authorization: str | None = Header(default=None)) -> dict[str, str]:
    # Local demo auth is intentionally transparent. A deployment should replace this with
    # JWT verification and case-team authorization before exposing the API.
    email = x_user_email or "priya@aegisflow.demo"
    role = x_role or ("manager" if email.startswith("marcus") else "aml_analyst")
    if authorization and authorization.lower().startswith("bearer "):
        try:
            payload = json.loads(base64.urlsafe_b64decode(authorization.split(" ", 1)[1] + "===").decode())
            email = payload.get("email", email)
            role = payload.get("role", role)
        except Exception:
            pass
    return {"id": email, "email": email, "role": role}


def require_manager(actor: dict[str, str]) -> None:
    if actor["role"] not in {"manager", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="manager approval is required")


def iso(value: datetime | None) -> str | None:
    return aware(value).isoformat() if value else None


def aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def tx_dict(tx: Transaction, decision: Decision | None = None) -> dict[str, Any]:
    return {
        "id": tx.id, "ts": iso(tx.ts), "account_id": tx.account_id, "counterparty_id": tx.counterparty_id,
        "merchant_id": tx.merchant_id, "device_id": tx.device_id, "ip_id": tx.ip_id, "amount": tx.amount,
        "currency": tx.currency, "channel": tx.channel, "country": tx.country, "status": tx.status,
        "decision": decision.decision if decision else None,
        "score": decision.calibrated_prob if decision else None,
        "reason_codes": decision.reason_codes if decision else [],
    }


def case_summary(session: Session, row: Case) -> dict[str, Any]:
    alerts = session.scalar(select(func.count(Alert.id)).where(Alert.case_id == row.id)) or 0
    evidence = session.scalar(select(func.count(EvidenceItem.id)).where(EvidenceItem.case_id == row.id)) or 0
    decisions = session.scalars(select(Decision).join(Transaction, Decision.transaction_id == Transaction.id).join(Alert, Alert.transaction_id == Transaction.id).where(Alert.case_id == row.id)).all()
    risk = max((x.calibrated_prob for x in decisions), default=min(0.99, row.priority / 100))
    return {
        "id": row.id, "title": row.title, "priority": round(row.priority, 1), "status": row.status,
        "assigned_to": row.assigned_to, "assignee_name": row.assignee_name, "sla_due": iso(row.sla_due),
        "disposition": row.disposition, "typology": row.typology, "account_ids": row.account_ids or [],
        "created_at": iso(row.created_at), "updated_at": iso(row.updated_at), "alert_count": alerts,
        "evidence_count": evidence, "risk_score": round(risk, 4),
    }


def _find_or_create_case(session: Session, account_id: str, typology: str, score: float, alert: Alert | None = None, related_accounts: list[str] | None = None) -> Case:
    account_set = set(related_accounts or [account_id])
    candidates = session.scalars(select(Case).where(Case.status.in_(["open", "investigating", "pending_review"]))).all()
    case = next((item for item in candidates if account_set.intersection(set(item.account_ids or []))), None)
    if not case:
        now = datetime.now(UTC)
        case = Case(id=new_id("case_"), title=f"{typology.replace('_', ' ').title()} · {account_id}", priority=min(99, max(42, score * 100)), status="open", sla_due=now + timedelta(hours=8), typology=typology, account_ids=sorted(account_set))
        session.add(case)
        metrics["cases_total"] = int(metrics["cases_total"]) + 1
    else:
        case.account_ids = sorted(set(case.account_ids or []).union(account_set))
        case.priority = min(99, max(case.priority, score * 100))
    session.flush()
    if alert:
        alert.case_id = case.id
    return case


def _persist_score(session: Session, request: ScoreRequest, result: Any, actor: dict[str, str]) -> dict[str, Any]:
    tx_id = result.transaction_id
    ts = request.ts or datetime.now(UTC)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    transaction = session.get(Transaction, tx_id)
    if not transaction:
        transaction = Transaction(id=tx_id, ts=ts, account_id=request.account_id, counterparty_id=request.counterparty_id, merchant_id=request.merchant_id, device_id=request.device_id, ip_id=request.ip_id, amount=request.amount, currency=request.currency.upper(), channel=request.channel, country=request.country.upper(), status="scored", raw=request.model_dump(mode="json"))
        session.add(transaction)
    decision = Decision(id=new_id("dec_"), transaction_id=tx_id, decision=result.decision, score=result.score, calibrated_prob=result.calibrated_prob, reason_codes=[x.model_dump() for x in result.reason_codes], rule_hits=[x.model_dump() for x in result.rule_hits], features=result.features, model_version=result.model_version, challenger=result.challenger, latency_ms=result.latency_ms, degraded=result.degraded, ts=ts)
    previous = session.scalar(select(Decision).where(Decision.transaction_id == tx_id))
    if previous:
        decision = previous
    else:
        session.add(decision)
    if result.decision in {"review", "decline"} and not previous:
        hit = result.rule_hits[0].label if result.rule_hits else "elevated model probability"
        alert = Alert(id=new_id("al_"), transaction_id=tx_id, alert_type="fraud_risk" if result.decision == "decline" else "risk_review", severity="critical" if result.decision == "decline" else "high", reason=hit)
        session.add(alert)
        typology = "network_anomaly" if result.features.get("graph_risk", 0) > 0.7 else ("smurfing" if result.features.get("velocity_1h", 0) >= 8 else "velocity_spike")
        case = _find_or_create_case(session, request.account_id, typology, result.calibrated_prob, alert, [request.account_id])
        audit(session, actor["id"], actor["role"], "alert.created", "case", case.id, {"alert_id": alert.id, "decision": result.decision, "reason_codes": [x.code for x in result.reason_codes]})
        metrics["alerts_total"] = int(metrics["alerts_total"]) + 1
    audit(session, actor["id"], actor["role"], "decision.created", "decision", decision.id, {"transaction_id": tx_id, "decision": result.decision, "model_version": result.model_version, "degraded": result.degraded})
    metrics["transactions_total"] = int(metrics["transactions_total"]) + (0 if previous else 1)
    metrics["score_latency_ms_sum"] = float(metrics["score_latency_ms_sum"]) + result.latency_ms
    session.commit()
    return {"transaction_id": tx_id, "decision": result.decision, "score": result.score, "calibrated_prob": result.calibrated_prob, "reason_codes": [x.model_dump() for x in result.reason_codes], "rule_hits": [x.model_dump() for x in result.rule_hits], "features": result.features, "model_version": result.model_version, "challenger": result.challenger, "latency_ms": result.latency_ms, "degraded": result.degraded, "feature_store_hit": result.feature_store_hit}


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    from .seed import seed_if_empty
    with SessionLocal() as session:
        seed_if_empty(session, scorer)


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "service": "aegisflow-platform", "environment": settings.app_env, "timestamp": datetime.now(UTC).isoformat()}


@app.get("/ready")
def ready(session: Session = Depends(session_scope)) -> dict[str, Any]:
    session.execute(select(func.count(User.id)))
    return {"status": "ready", "database": "ok", "online_features": "in-memory-compatible"}


@app.get("/metrics")
def prometheus_metrics() -> Response:
    score_count = max(1, int(metrics["transactions_total"]))
    body = "\n".join([
        "# HELP aegisflow_transactions_total Transactions scored",
        "# TYPE aegisflow_transactions_total counter",
        f"aegisflow_transactions_total {metrics['transactions_total']}",
        "# HELP aegisflow_alerts_total Alerts generated",
        "# TYPE aegisflow_alerts_total counter",
        f"aegisflow_alerts_total {metrics['alerts_total']}",
        "# HELP aegisflow_score_latency_ms_avg Average scorer latency in milliseconds",
        "# TYPE aegisflow_score_latency_ms_avg gauge",
        f"aegisflow_score_latency_ms_avg {float(metrics['score_latency_ms_sum']) / score_count:.4f}",
        "# HELP aegisflow_challenger_disagreement_ratio Shadow disagreement ratio",
        "# TYPE aegisflow_challenger_disagreement_ratio gauge",
        f"aegisflow_challenger_disagreement_ratio {scorer.shadow_disagreement_rate:.6f}",
    ]) + "\n"
    return Response(content=body, media_type="text/plain; version=0.0.4")


@app.post("/api/v1/auth/login")
def login(payload: LoginIn) -> dict[str, Any]:
    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.email == payload.email))
    if not user or payload.password != "demo":
        raise HTTPException(status_code=401, detail="invalid demo credentials")
    token = base64.urlsafe_b64encode(json.dumps({"email": user.email, "role": user.role}).encode()).decode().rstrip("=")
    return {"access_token": token, "token_type": "bearer", "user": {"id": user.id, "email": user.email, "display_name": user.display_name, "role": user.role}}


@app.get("/api/v1/overview")
def overview(session: Session = Depends(session_scope), actor: dict[str, str] = Depends(actor_context)) -> dict[str, Any]:
    decisions = session.scalars(select(Decision).order_by(Decision.ts.desc()).limit(200)).all()
    cases = session.scalars(select(Case).order_by(Case.priority.desc()).limit(100)).all()
    counts = {key: sum(1 for d in decisions if d.decision == key) for key in ("approve", "review", "decline")}
    return {
        "kpis": {"transactions_today": len(decisions), "review_rate": round((counts["review"] + counts["decline"]) / max(1, len(decisions)) * 100, 1), "open_cases": sum(1 for c in cases if c.status != "closed"), "sla_at_risk": sum(1 for c in cases if c.status != "closed" and aware(c.sla_due) < datetime.now(UTC) + timedelta(hours=4)), "avg_latency_ms": round(sum(d.latency_ms for d in decisions) / max(1, len(decisions)), 2), "feature_hit_rate": round(sum(1 for d in decisions if not d.degraded) / max(1, len(decisions)) * 100, 1)},
        "decision_mix": counts,
        "live": [decision_dict(session, d) for d in decisions[:12]],
        "activity": activity_rows(session, 8),
        "role": actor["role"],
    }


def decision_dict(session: Session, d: Decision) -> dict[str, Any]:
    tx = session.get(Transaction, d.transaction_id)
    return {"id": d.id, "transaction_id": d.transaction_id, "ts": iso(d.ts), "account_id": tx.account_id if tx else "unknown", "amount": tx.amount if tx else 0, "currency": tx.currency if tx else "USD", "channel": tx.channel if tx else "card", "decision": d.decision, "score": d.calibrated_prob, "latency_ms": d.latency_ms, "reason_codes": d.reason_codes or [], "rule_hits": d.rule_hits or [], "model_version": d.model_version, "degraded": d.degraded}


@app.get("/api/v1/decisions")
def decisions(limit: int = Query(default=50, ge=1, le=200), session: Session = Depends(session_scope)) -> dict[str, Any]:
    rows = session.scalars(select(Decision).order_by(Decision.ts.desc()).limit(limit)).all()
    return {"items": [decision_dict(session, row) for row in rows], "count": len(rows)}


@app.post("/api/v1/score")
def score(payload: ScoreRequest, session: Session = Depends(session_scope), actor: dict[str, str] = Depends(actor_context)) -> dict[str, Any]:
    transaction_id = payload.id or str(uuid.uuid4())
    request_data = payload.model_dump(exclude_none=True)
    request_data.update(id=transaction_id, ts=payload.ts or datetime.now(UTC))
    request = CoreScoreRequest(**request_data)
    started = time.perf_counter()
    result = scorer.score(request)
    scorer.feature_reader.observe(request)
    result.latency_ms = round(max(result.latency_ms, (time.perf_counter() - started) * 1000), 3)
    return _persist_score(session, payload.model_copy(update={"id": transaction_id, "ts": request.ts}), result, actor)


@app.post("/api/v1/transactions")
def ingest(payload: TransactionIn, session: Session = Depends(session_scope), actor: dict[str, str] = Depends(actor_context)) -> dict[str, Any]:
    return score(ScoreRequest(**payload.model_dump()), session, actor)


@app.get("/api/v1/cases")
def cases(status_filter: str | None = Query(default=None, alias="status"), sort: str = Query(default="sla"), limit: int = Query(default=50, ge=1, le=200), session: Session = Depends(session_scope)) -> dict[str, Any]:
    query = select(Case)
    if status_filter:
        query = query.where(Case.status == status_filter)
    query = query.order_by(Case.sla_due.asc() if sort == "sla" else Case.priority.desc()).limit(limit)
    rows = session.scalars(query).all()
    return {"items": [case_summary(session, row) for row in rows], "count": len(rows)}


@app.get("/api/v1/cases/{case_id}")
def case_detail(case_id: str, session: Session = Depends(session_scope)) -> dict[str, Any]:
    row = session.get(Case, case_id)
    if not row:
        raise HTTPException(404, "case not found")
    alerts = session.scalars(select(Alert).where(Alert.case_id == case_id).order_by(Alert.created_at.desc())).all()
    evidence = session.scalars(select(EvidenceItem).where(EvidenceItem.case_id == case_id).order_by(EvidenceItem.created_at)).all()
    drafts = session.scalars(select(SARDraft).where(SARDraft.case_id == case_id).order_by(SARDraft.version.desc())).all()
    audit_rows = session.scalars(select(AuditLog).where(AuditLog.resource_id == case_id).order_by(AuditLog.created_at.desc()).limit(20)).all()
    transactions = []
    for alert in alerts:
        tx = session.get(Transaction, alert.transaction_id)
        dec = session.scalar(select(Decision).where(Decision.transaction_id == alert.transaction_id))
        if tx:
            transactions.append({**tx_dict(tx, dec), "alert_id": alert.id, "alert_type": alert.alert_type, "severity": alert.severity, "reason": alert.reason})
    result = case_summary(session, row)
    result.update({"alerts": transactions, "evidence": [{"id": e.id, "kind": e.kind, "title": e.title, "payload": e.payload, "source_ref": e.source_ref, "created_by": e.created_by, "created_at": iso(e.created_at)} for e in evidence], "drafts": [{"id": d.id, "version": d.version, "narrative_md": d.narrative_md, "citations": d.citations, "status": d.status, "author": d.author, "reviewed_by": d.reviewed_by, "review_rationale": d.review_rationale, "created_at": iso(d.created_at)} for d in drafts], "graph": _build_graph(session, row), "audit": [{"id": a.id, "actor_id": a.actor_id, "actor_role": a.actor_role, "action": a.action, "detail": a.detail, "created_at": iso(a.created_at)} for a in audit_rows]})
    return result


@app.get("/api/v1/cases/{case_id}/graph")
def case_graph(case_id: str, hops: int = Query(default=2, ge=1, le=3), session: Session = Depends(session_scope)) -> dict[str, Any]:
    row = session.get(Case, case_id)
    if not row:
        raise HTTPException(404, "case not found")
    graph = _build_graph(session, row)
    graph["hops"] = hops
    return graph


@app.post("/api/v1/cases/{case_id}/investigate")
def investigate(case_id: str, background_tasks: BackgroundTasks, session: Session = Depends(session_scope), actor: dict[str, str] = Depends(actor_context)) -> dict[str, Any]:
    row = session.get(Case, case_id)
    if not row:
        raise HTTPException(404, "case not found")
    row.status = "investigating"
    audit(session, actor["id"], actor["role"], "investigation.started", "case", case_id, {"workflow": "typed-specialists"})
    session.commit()
    # The deterministic local graph is fast and makes the demo immediately inspectable.
    with SessionLocal() as worker_session:
        worker_case = worker_session.get(Case, case_id)
        result = run_investigation(worker_session, worker_case, actor["id"])
        audit(worker_session, actor["id"], actor["role"], "investigation.completed", "case", case_id, {"evidence_count": result["evidence_count"], "qa": result["qa"]})
        worker_session.commit()
    return {"job_id": new_id("job_"), "case_id": case_id, **result, "status": "completed", "case_status": result.get("status")}


@app.post("/api/v1/cases/{case_id}/disposition")
def disposition(case_id: str, payload: DispositionIn, session: Session = Depends(session_scope), actor: dict[str, str] = Depends(actor_context)) -> dict[str, Any]:
    row = session.get(Case, case_id)
    if not row:
        raise HTTPException(404, "case not found")
    row.disposition = payload.disposition
    row.disposition_rationale = payload.rationale
    row.status = "closed"
    audit(session, actor["id"], actor["role"], "case.dispositioned", "case", case_id, {"disposition": payload.disposition, "rationale": payload.rationale})
    session.commit()
    return case_summary(session, row)


@app.get("/api/v1/sar/{case_id}/draft")
def get_draft(case_id: str, session: Session = Depends(session_scope)) -> dict[str, Any]:
    draft = session.scalar(select(SARDraft).where(SARDraft.case_id == case_id).order_by(SARDraft.version.desc()))
    if not draft:
        raise HTTPException(404, "no investigation draft exists")
    return {"id": draft.id, "case_id": case_id, "version": draft.version, "narrative_md": draft.narrative_md, "citations": draft.citations, "status": draft.status, "author": draft.author, "reviewed_by": draft.reviewed_by, "review_rationale": draft.review_rationale, "created_at": iso(draft.created_at)}


@app.put("/api/v1/sar/{case_id}/draft")
def edit_draft(case_id: str, payload: EditDraftIn, session: Session = Depends(session_scope), actor: dict[str, str] = Depends(actor_context)) -> dict[str, Any]:
    case = session.get(Case, case_id)
    if not case:
        raise HTTPException(404, "case not found")
    latest = session.scalar(select(SARDraft).where(SARDraft.case_id == case_id).order_by(SARDraft.version.desc()))
    version = (latest.version if latest else 0) + 1
    draft = SARDraft(id=new_id("sar_"), case_id=case_id, version=version, narrative_md=payload.narrative_md, citations=payload.citations or (latest.citations if latest else []), status="edited", author="analyst", reviewed_by=None)
    session.add(draft)
    case.status = "pending_review"
    audit(session, actor["id"], actor["role"], "sar.edited", "sar_draft", draft.id, {"case_id": case_id, "version": version})
    session.commit()
    return {"id": draft.id, "case_id": case_id, "version": draft.version, "narrative_md": draft.narrative_md, "citations": draft.citations, "status": draft.status, "author": draft.author, "created_at": iso(draft.created_at)}


@app.post("/api/v1/sar/{case_id}/approve")
def approve_sar(case_id: str, payload: ApprovalIn, session: Session = Depends(session_scope), actor: dict[str, str] = Depends(actor_context)) -> dict[str, Any]:
    require_manager(actor)
    case = session.get(Case, case_id)
    draft = session.scalar(select(SARDraft).where(SARDraft.case_id == case_id).order_by(SARDraft.version.desc()))
    if not case or not draft:
        raise HTTPException(404, "case or SAR draft not found")
    if not draft.citations:
        raise HTTPException(409, "draft has no evidence citations")
    draft.status = "approved"
    draft.reviewed_by = actor["id"]
    draft.review_rationale = payload.rationale
    case.status = "closed"
    case.disposition = "sar_filed"
    case.disposition_rationale = payload.rationale
    audit(session, actor["id"], actor["role"], "sar.approved", "sar_draft", draft.id, {"case_id": case_id, "version": draft.version, "rationale": payload.rationale, "autonomous": False})
    metrics["approvals_total"] = int(metrics["approvals_total"]) + 1
    session.commit()
    return {"case_id": case_id, "draft_id": draft.id, "status": draft.status, "export_ref": f"/api/v1/sar/{case_id}/export", "approved_by": actor["id"]}


@app.get("/api/v1/sar/{case_id}/export")
def export_sar(case_id: str, session: Session = Depends(session_scope)) -> dict[str, Any]:
    case = session.get(Case, case_id)
    draft = session.scalar(select(SARDraft).where(SARDraft.case_id == case_id).order_by(SARDraft.version.desc()))
    if not case or not draft:
        raise HTTPException(404, "case or draft not found")
    if draft.status != "approved":
        raise HTTPException(409, "only approved drafts can be exported")
    return {"form": "AegisFlow synthetic SAR export", "case_id": case.id, "status": "approved", "subject_accounts": case.account_ids, "activity_type": case.typology, "narrative": draft.narrative_md, "citations": draft.citations, "reviewed_by": draft.reviewed_by, "review_rationale": draft.review_rationale}


@app.get("/api/v1/thresholds")
def get_thresholds(session: Session = Depends(session_scope)) -> dict[str, Any]:
    row = session.get(ThresholdConfig, 1)
    if not row:
        row = ThresholdConfig(id=1, review_threshold=scorer.thresholds.review, decline_threshold=scorer.thresholds.decline)
        session.add(row)
        session.commit()
    return {"review_t": row.review_threshold, "decline_t": row.decline_threshold, "version": row.version, "updated_by": row.updated_by, "updated_at": iso(row.updated_at)}


@app.put("/api/v1/thresholds")
def update_thresholds(payload: ThresholdsIn, session: Session = Depends(session_scope), actor: dict[str, str] = Depends(actor_context)) -> dict[str, Any]:
    require_manager(actor)
    if payload.review_t >= payload.decline_t:
        raise HTTPException(422, "review threshold must be below decline threshold")
    row = session.get(ThresholdConfig, 1)
    if not row:
        row = ThresholdConfig(id=1)
        session.add(row)
    row.review_threshold = payload.review_t
    row.decline_threshold = payload.decline_t
    row.version += 1
    row.updated_by = actor["id"]
    row.updated_at = datetime.now(UTC)
    scorer.update_thresholds(payload.review_t, payload.decline_t)
    audit(session, actor["id"], actor["role"], "thresholds.updated", "threshold_config", "1", {"review_t": payload.review_t, "decline_t": payload.decline_t, "version": row.version})
    session.commit()
    return {"review_t": row.review_threshold, "decline_t": row.decline_threshold, "version": row.version, "updated_by": row.updated_by, "updated_at": iso(row.updated_at)}


@app.get("/api/v1/models")
def models() -> dict[str, Any]:
    return {"champion": {"name": "fraud-champion", "version": scorer.model_version, "stage": "Production", "calibration": "isotonic", "features": 12, "deployed_at": "2026-09-22T08:00:00Z"}, "challenger": {"name": "fraud-challenger-graph", "version": scorer.challenger_version, "stage": "Shadow", "disagreement_rate": round(scorer.shadow_disagreement_rate, 4), "scored": scorer.shadow_scored, "lift_estimate": "+8.4%"}, "promotion_policy": {"minimum_lift": 0.05, "minimum_window": 10000, "human_approval": True}}


@app.get("/api/v1/drift")
def drift() -> dict[str, Any]:
    return {"window": "last 24 hours", "status": "healthy", "psi_threshold": 0.2, "features": [{"name": "velocity_1h", "psi": 0.06, "status": "healthy"}, {"name": "amount_zscore", "psi": 0.11, "status": "healthy"}, {"name": "graph_risk", "psi": 0.17, "status": "watch"}, {"name": "device_sharing_degree", "psi": 0.04, "status": "healthy"}], "score_distribution": {"psi": 0.08, "status": "healthy"}, "label_delay_days": 2.4}


def activity_rows(session: Session, limit: int = 10) -> list[dict[str, Any]]:
    rows = session.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)).all()
    return [{"id": row.id, "action": row.action, "resource_type": row.resource_type, "resource_id": row.resource_id, "actor": row.actor_id.split("@")[0], "created_at": iso(row.created_at), "detail": row.detail} for row in rows]


@app.get("/api/v1/activity")
def activity(limit: int = Query(default=30, ge=1, le=100), session: Session = Depends(session_scope)) -> dict[str, Any]:
    return {"items": activity_rows(session, limit)}
