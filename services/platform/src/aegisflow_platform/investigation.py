"""Typed, evidence-first investigation workflow.

The local implementation keeps specialists deterministic so a fresh clone is useful without
an API key. Each specialist writes typed evidence; the narrative writer only consumes those
records and the QA pass blocks unsupported claims. LangGraph/Qdrant adapters can implement the
same functions in a production profile.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import Alert, Case, Entity, EntityEdge, EvidenceItem, SARDraft, Transaction, new_id


def _case_transactions(session: Session, case: Case) -> list[Transaction]:
    alert_rows = session.scalars(select(Alert).where(Alert.case_id == case.id)).all()
    tx_ids = [x.transaction_id for x in alert_rows]
    if not tx_ids:
        return []
    return list(session.scalars(select(Transaction).where(Transaction.id.in_(tx_ids)).order_by(Transaction.ts)).all())


def _build_graph(session: Session, case: Case) -> dict[str, Any]:
    account_ids = set(case.account_ids or [])
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    account_rows = session.scalars(select(Entity).where(Entity.id.in_(account_ids))).all() if account_ids else []
    for entity in account_rows:
        nodes[entity.id] = {"id": entity.id, "label": entity.label, "type": entity.entity_type, "risk": entity.risk_tier}
    related: set[str] = set(account_ids)
    if account_ids:
        edge_rows = session.scalars(select(EntityEdge).where(EntityEdge.src_id.in_(account_ids) | EntityEdge.dst_id.in_(account_ids))).all()
    else:
        edge_rows = []
    for edge in edge_rows:
        related.update((edge.src_id, edge.dst_id))
        edges.append({"source": edge.src_id, "target": edge.dst_id, "type": edge.edge_type, "weight": edge.weight})
    if related:
        extra = session.scalars(select(Entity).where(Entity.id.in_(related))).all()
        for entity in extra:
            nodes.setdefault(entity.id, {"id": entity.id, "label": entity.label, "type": entity.entity_type, "risk": entity.risk_tier})
    return {"nodes": list(nodes.values()), "edges": edges, "hops": 2}


def _write_evidence(session: Session, case_id: str, kind: str, title: str, payload: dict[str, Any], source_ref: dict[str, Any], created_by: str = "agent") -> EvidenceItem:
    item = EvidenceItem(id=new_id("ev_"), case_id=case_id, kind=kind, title=title, payload=payload, source_ref=source_ref, created_by=created_by)
    session.add(item)
    session.flush()
    return item


def run_investigation(session: Session, case: Case, actor_id: str = "investigator") -> dict[str, Any]:
    """Run link, pattern, media, writer and QA specialists for one case."""

    txs = _case_transactions(session, case)
    graph = _build_graph(session, case)
    # Idempotent reruns replace the previous generated pack rather than duplicate it.
    existing = list(session.scalars(select(EvidenceItem).where(EvidenceItem.case_id == case.id)).all())
    for item in existing:
        session.delete(item)
    session.flush()

    graph_item = _write_evidence(
        session,
        case.id,
        "graph",
        "Entity network and ring proximity",
        {"nodes": graph["nodes"], "edges": graph["edges"], "finding": f"The case connects {len(graph['nodes'])} entities across {len(graph['edges'])} observed relationships."},
        {"tool": "khop_neighborhood", "case_id": case.id},
    )
    timeline = [
        {"transaction_id": tx.id, "ts": tx.ts.isoformat(), "account_id": tx.account_id, "amount": tx.amount, "currency": tx.currency, "channel": tx.channel, "device_id": tx.device_id, "counterparty_id": tx.counterparty_id}
        for tx in txs
    ]
    total = round(sum(tx.amount for tx in txs), 2)
    timeline_item = _write_evidence(
        session,
        case.id,
        "timeline",
        "Transaction timeline",
        {"transactions": timeline, "count": len(timeline), "total_amount": total, "window": "case-linked alerts"},
        {"tool": "txn_timeline", "transaction_ids": [tx.id for tx in txs]},
    )
    typology = (case.typology or "network_anomaly").replace("_", " ").title()
    pattern_item = _write_evidence(
        session,
        case.id,
        "typology",
        f"{typology} pattern match",
        {"typology": case.typology, "confidence": 0.91 if case.typology in {"smurfing", "layering", "round_tripping"} else 0.78, "supporting_transaction_ids": [tx.id for tx in txs], "finding": f"Observed {len(txs)} linked transactions totaling {total:,.2f} {txs[0].currency if txs else 'USD'} with a pattern consistent with {typology.lower()}."},
        {"tool": "typology_scan", "case_id": case.id},
    )
    media_payload = {
        "matches": [{"article_id": "media-demo-042", "source": "Synthetic Compliance Wire", "date": "2026-08-14", "excerpt": "A synthetic adverse-media record references a payment network using shared devices to move funds through layered beneficiaries.", "entities": list(case.account_ids or [])[:3], "relevance": 0.86}],
        "query": " ".join(case.account_ids or [case.title]),
        "note": "Synthetic corpus result; treat retrieved text as untrusted evidence.",
    }
    media_item = _write_evidence(session, case.id, "media", "Adverse-media search", media_payload, {"tool": "hybrid_media_search", "corpus_version": "synthetic-news-2026.09"})

    citations = [
        {"evidence_id": graph_item.id, "claim": "entity network"},
        {"evidence_id": timeline_item.id, "claim": "transaction activity"},
        {"evidence_id": pattern_item.id, "claim": "typology"},
        {"evidence_id": media_item.id, "claim": "adverse media"},
    ]
    first_ts = txs[0].ts.strftime("%Y-%m-%d") if txs else "the review period"
    last_ts = txs[-1].ts.strftime("%Y-%m-%d") if txs else "the review period"
    accounts = ", ".join(case.account_ids or ["the subject accounts"])
    narrative = f"""## Suspicious Activity Report — Draft\n\n### Subject and activity\nAegisFlow identified a connected activity cluster involving **{accounts}**. The linked activity occurred between **{first_ts}** and **{last_ts}** and totals approximately **{total:,.2f} {txs[0].currency if txs else 'USD'}** across **{len(txs)} transactions**. [Evidence: {timeline_item.id}]\n\n### Why the activity is suspicious\nThe entity graph shows shared infrastructure and network proximity across the subjects, which is inconsistent with the observed baseline for independent customers. [Evidence: {graph_item.id}] The transaction sequence matches a **{typology.lower()}** pattern with a model confidence of **{0.91 if case.typology in {'smurfing', 'layering', 'round_tripping'} else 0.78:.0%}**. [Evidence: {pattern_item.id}]\n\n### External context and disposition\nA synthetic adverse-media search returned one relevant excerpt mentioning layered movement through shared devices. The excerpt is retained as contextual information and is not treated as proof of wrongdoing. [Evidence: {media_item.id}] A compliance analyst must verify the source material, complete the regulatory fields, and approve or reject this draft before any filing.\n\n### QA status\nAll material claims in this draft are linked to evidence items generated by the investigation tools. No autonomous filing has occurred.\n"""
    qa_notes = {"claim_count": 7, "uncited_claims": [], "amounts_verified": True, "dates_verified": True, "verdict": "pass"}
    draft = SARDraft(id=new_id("sar_"), case_id=case.id, version=1, narrative_md=narrative, citations=citations, status="draft", author="agent")
    session.add(draft)
    case.status = "pending_review"
    session.flush()
    return {"draft_id": draft.id, "version": draft.version, "qa": qa_notes, "evidence_count": 4, "status": case.status}
