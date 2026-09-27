"""Auditable, pure-function rules. Rules never mutate feature state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RuleHitData:
    rule_id: str
    label: str
    severity: str
    action: str
    detail: str


def evaluate_rules(request: Any, features: dict[str, Any]) -> list[RuleHitData]:
    hits: list[RuleHitData] = []

    if features.get("sanctions_hit"):
        hits.append(RuleHitData("SAN-001", "Sanctions list match", "critical", "decline", "Entity matched the demo sanctions reference list"))
    if features.get("impossible_travel"):
        hits.append(RuleHitData("GEO-004", "Impossible travel", "high", "decline", "Recent locations exceed the configured travel-speed threshold"))
    if float(features.get("velocity_1h", 0)) >= 8:
        hits.append(RuleHitData("VEL-001", "One-hour velocity spike", "high", "review", f"{int(features['velocity_1h'])} payments observed in the rolling hour"))
    if float(features.get("velocity_24h", 0)) >= 20:
        hits.append(RuleHitData("VEL-002", "Daily velocity spike", "medium", "review", f"{int(features['velocity_24h'])} payments observed in the rolling day"))
    if bool(features.get("new_device")) and float(getattr(request, "amount", 0)) >= 1_500:
        hits.append(RuleHitData("DEV-003", "High-value new device", "medium", "review", "High-value payment originated from an unseen device"))
    if float(getattr(request, "amount", 0)) >= 15_000:
        hits.append(RuleHitData("AMT-001", "High-value transfer", "medium", "review", "Amount exceeds the high-value monitoring threshold"))
    if float(features.get("graph_risk", 0)) >= 0.78:
        hits.append(RuleHitData("NET-007", "Known-risk network proximity", "high", "review", "Account is close to a known-fraud component"))
    return hits
