from __future__ import annotations

from collections import defaultdict
from typing import Any


def txn_timeline(transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(transactions, key=lambda row: row.get("ts", ""))


def velocity_summary(transactions: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = defaultdict(int)
    for transaction in transactions:
        counts[transaction.get("account_id", "unknown")] += 1
    return {"count": len(transactions), "by_account": dict(counts), "total_amount": round(sum(float(row.get("amount", 0)) for row in transactions), 2)}
