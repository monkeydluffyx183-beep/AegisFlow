from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
from typing import Any

from scoring.schemas import ScoreRequest as CoreScoreRequest
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import Alert, Case, Decision, Entity, EntityEdge, GroundTruthLabel, ThresholdConfig, Transaction, User, audit


def seed_if_empty(session: Session, scorer: Any) -> None:
    if session.scalar(select(User.id).limit(1)):
        return
    random.seed(42)
    now = datetime.now(UTC)
    users = [
        User(id="usr_priya", email="priya@aegisflow.demo", display_name="Priya Nair", role="aml_analyst"),
        User(id="usr_marcus", email="marcus@aegisflow.demo", display_name="Marcus Lee", role="manager"),
        User(id="usr_fraud", email="fraud@aegisflow.demo", display_name="Sofia Chen", role="fraud_analyst"),
        User(id="usr_admin", email="admin@aegisflow.demo", display_name="Aegis Admin", role="admin"),
    ]
    session.add_all(users)
    session.add(ThresholdConfig(id=1, review_threshold=scorer.thresholds.review, decline_threshold=scorer.thresholds.decline, updated_by="system"))

    accounts = [
        ("acct-ring-1042", "A. K. Holdings", "critical"),
        ("acct-ring-2281", "Northstar Trading", "high"),
        ("acct-ring-3988", "Mosaic Services", "high"),
        ("acct-ring-4406", "Harborline LLC", "elevated"),
        ("acct-9071", "Jordan Williams", "standard"),
        ("acct-1180", "Maya Patel", "standard"),
        ("acct-5520", "Elena García", "standard"),
        ("acct-7312", "Noah Brown", "elevated"),
    ]
    for account_id, label, risk in accounts:
        session.add(Entity(id=account_id, entity_type="account", label=label, risk_tier=risk))
    for device_id, label, risk in [("dev-shared-77", "Shared fingerprint 77", "critical"), ("dev-9071", "Jordan device", "standard"), ("dev-1180", "Maya device", "standard"), ("dev-5520", "Elena device", "standard"), ("dev-7312", "Noah device", "elevated")]:
        session.add(Entity(id=device_id, entity_type="device", label=label, risk_tier=risk))
    for ip_id, label in [("ip-198-51-100-8", "198.51.100.8"), ("ip-203-0-113-44", "203.0.113.44"), ("ip-203-0-113-55", "203.0.113.55")]:
        session.add(Entity(id=ip_id, entity_type="ip", label=label, risk_tier="standard"))
    for src, dst, edge_type, weight in [
        ("acct-ring-1042", "dev-shared-77", "uses_device", 1.0), ("acct-ring-2281", "dev-shared-77", "uses_device", 0.92), ("acct-ring-3988", "dev-shared-77", "uses_device", 0.88), ("acct-ring-4406", "dev-shared-77", "uses_device", 0.75),
        ("acct-ring-1042", "ip-198-51-100-8", "uses_ip", 1.0), ("acct-ring-2281", "ip-198-51-100-8", "uses_ip", 0.94), ("acct-ring-3988", "ip-203-0-113-44", "uses_ip", 0.8),
        ("acct-9071", "dev-9071", "uses_device", 1.0), ("acct-1180", "dev-1180", "uses_device", 1.0), ("acct-5520", "dev-5520", "uses_device", 1.0), ("acct-7312", "dev-7312", "uses_device", 1.0),
        ("acct-ring-1042", "acct-ring-2281", "transfers_to", 0.82), ("acct-ring-2281", "acct-ring-3988", "transfers_to", 0.79), ("acct-ring-3988", "acct-ring-1042", "transfers_to", 0.76),
    ]:
        dst_type = {"uses_device": "device", "uses_ip": "ip"}.get(edge_type, "account")
        session.add(EntityEdge(src_type="account", src_id=src, dst_type=dst_type, dst_id=dst, edge_type=edge_type, weight=weight))

    for account_id, graph_risk, share_degree, avg in [("acct-ring-1042", .94, 8, 250), ("acct-ring-2281", .87, 7, 320), ("acct-ring-3988", .82, 6, 190), ("acct-ring-4406", .72, 5, 450), ("acct-9071", .06, 0, 180), ("acct-1180", .04, 0, 145), ("acct-5520", .08, 0, 210), ("acct-7312", .18, 2, 290)]:
        scorer.seed_account(account_id, graph_risk=graph_risk, device_sharing_degree=share_degree, avg_amount=avg, amount_std=max(avg * .5, 90), known_device=f"dev-{account_id.removeprefix('acct-')}")

    ring_case = Case(id="case_ring_1042", title="Coordinated smurfing · shared device cluster", priority=96.4, status="pending_review", sla_due=now + timedelta(hours=3, minutes=18), assigned_to="usr_priya", assignee_name="Priya Nair", typology="smurfing", account_ids=["acct-ring-1042", "acct-ring-2281", "acct-ring-3988", "acct-ring-4406"], created_at=now - timedelta(hours=5))
    wire_case = Case(id="case_wire_9071", title="High-value transfer · beneficiary mismatch", priority=71.8, status="open", sla_due=now + timedelta(hours=7, minutes=42), assigned_to=None, assignee_name=None, typology="layering", account_ids=["acct-9071", "acct-7312"], created_at=now - timedelta(hours=2))
    review_case = Case(id="case_review_7312", title="Device sharing · elevated velocity", priority=54.1, status="investigating", sla_due=now + timedelta(hours=11), assigned_to="usr_fraud", assignee_name="Sofia Chen", typology="network_anomaly", account_ids=["acct-7312"], created_at=now - timedelta(minutes=48))
    session.add_all([ring_case, wire_case, review_case])
    session.flush()

    # Ring: fourteen small movements in a short window. The labels are deliberately not used by scoring.
    tx_specs: list[tuple[str, str, float, str, str, str, list[str]]] = []
    for index in range(14):
        account = ["acct-ring-1042", "acct-ring-2281", "acct-ring-3988", "acct-ring-4406"][index % 4]
        tx_specs.append((account, f"acct-ring-{[2281,3988,1042,4406][index % 4]}", round(780 + index * 47.5, 2), "dev-shared-77", "ip-198-51-100-8" if index % 3 else "ip-203-0-113-44", "case_ring_1042", ["smurfing", "fraud_ring"]))
    # Additional benign traffic keeps the live feed realistic.
    for index, account in enumerate(["acct-9071", "acct-1180", "acct-5520", "acct-7312", "acct-9071", "acct-1180", "acct-5520", "acct-7312"]):
        tx_specs.append((account, "merchant-retail-" + str(index % 3), round(38 + index * 21.3, 2), f"dev-{account.removeprefix('acct-')}", "ip-203-0-113-55", "case_review_7312" if account == "acct-7312" else "", []))
    for index, (account, counterparty, amount, device, ip, target_case, labels) in enumerate(tx_specs):
        transaction_id = f"tx-demo-{index + 1:03d}"
        timestamp = now - timedelta(minutes=(len(tx_specs) - index) * 4)
        request = CoreScoreRequest(id=transaction_id, account_id=account, counterparty_id=counterparty, merchant_id=None if account.startswith("acct-ring") else "merchant-retail", device_id=device, ip_id=ip, amount=amount, currency="USD", channel="transfer" if account.startswith("acct-ring") else "card", country="US", ts=timestamp, labels=labels)
        result = scorer.score(request)
        scorer.feature_reader.observe(request)
        session.add(Transaction(id=transaction_id, ts=timestamp, account_id=account, counterparty_id=counterparty, merchant_id=request.merchant_id, device_id=device, ip_id=ip, amount=amount, currency="USD", channel=request.channel, country="US", status="scored", raw={"synthetic_labels": labels}))
        decision_id = f"dec-demo-{index + 1:03d}"
        session.add(Decision(id=decision_id, transaction_id=transaction_id, decision=result.decision, score=result.score, calibrated_prob=result.calibrated_prob, reason_codes=[x.model_dump() for x in result.reason_codes], rule_hits=[x.model_dump() for x in result.rule_hits], features=result.features, model_version=result.model_version, challenger=result.challenger, latency_ms=result.latency_ms, degraded=False, ts=timestamp))
        session.add(GroundTruthLabel(transaction_id=transaction_id, is_fraud=bool(labels)))
        if target_case:
            session.add(Alert(id=f"al-demo-{index + 1:03d}", transaction_id=transaction_id, case_id=target_case, alert_type="aml_typology" if labels else "risk_review", severity="critical" if labels else "medium", reason=("Smurfing pattern member" if labels else "Device/velocity review"), created_at=timestamp))
        elif result.decision in {"review", "decline"}:
            # Keep any naturally generated alert attached to a useful seeded queue item.
            session.add(Alert(id=f"al-demo-auto-{index + 1:03d}", transaction_id=transaction_id, case_id="case_review_7312", alert_type="risk_review", severity="medium", reason="Model review threshold"))
    session.flush()
    audit(session, "system", "admin", "demo.seeded", "platform", "aegisflow", {"transactions": len(tx_specs), "cases": 3, "synthetic": True})
    session.commit()
    # Generate the initial pack for the primary ring case, using the same investigation path
    # as an analyst click, so the console opens with useful evidence.
    from .investigation import run_investigation
    primary = session.get(Case, "case_ring_1042")
    if primary:
        run_investigation(session, primary, "system")
        session.commit()


def main() -> None:
    from scoring.decision import Thresholds
    from scoring.engine import ScoringEngine

    from .config import settings
    from .db import SessionLocal, init_db
    init_db()
    with SessionLocal() as session:
        seed_if_empty(session, ScoringEngine(Thresholds(settings.review_threshold, settings.decline_threshold)))
        print("AegisFlow demo data is ready")


if __name__ == "__main__":
    main()
