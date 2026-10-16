from __future__ import annotations

from collections import defaultdict
from typing import Any


def typology_scan(transactions: list[dict[str, Any]], structuring_ceiling: float = 10_000) -> list[dict[str, Any]]:
    """Deterministic detectors that agents interpret but never override."""
    findings: list[dict[str, Any]] = []
    if not transactions:
        return findings
    amounts = [float(row.get("amount", 0)) for row in transactions]
    if len(transactions) >= 5 and sum(1 for amount in amounts if amount < structuring_ceiling) >= 5:
        findings.append({"typology": "smurfing", "confidence": min(0.99, 0.62 + len(transactions) * 0.02), "transaction_ids": [row["transaction_id"] for row in transactions]})
    ordered = sorted(transactions, key=lambda row: row.get("ts", ""))
    if len(ordered) >= 3 and len({row.get("account_id") for row in ordered}) >= 2:
        findings.append({"typology": "layering", "confidence": 0.74, "transaction_ids": [row["transaction_id"] for row in ordered]})
    return findings


def velocity_summary(transactions: list[dict[str, Any]]) -> dict[str, Any]:
    by_account: dict[str, int] = defaultdict(int)
    for row in transactions:
        by_account[row.get("account_id", "unknown")] += 1
    return {"transaction_count": len(transactions), "by_account": dict(by_account), "total_amount": round(sum(float(row.get("amount", 0)) for row in transactions), 2)}
