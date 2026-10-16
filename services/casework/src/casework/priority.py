from __future__ import annotations

from datetime import UTC, datetime, timedelta


def priority_score(*, probability: float, amount: float, severity: str, account_risk: float = 0.0, typology_match: bool = False) -> float:
    severity_weight = {"low": 5, "medium": 14, "high": 24, "critical": 34}.get(severity, 10)
    amount_weight = min(20, max(0, amount / 1_000))
    return round(min(99.9, probability * 42 + severity_weight + amount_weight + account_risk * 18 + (12 if typology_match else 0)), 1)


def sla_due(now: datetime | None = None, priority: float = 50) -> datetime:
    now = now or datetime.now(UTC)
    hours = 4 if priority >= 80 else 8 if priority >= 60 else 24
    return now.replace(microsecond=0) + timedelta(hours=hours)
