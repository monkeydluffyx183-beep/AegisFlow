from __future__ import annotations

from typing import Any

_REASON_LABELS = {
    "velocity_1h": "One-hour payment velocity",
    "velocity_24h": "Daily payment velocity",
    "amount_zscore": "Amount above account baseline",
    "device_sharing_degree": "Device shared across accounts",
    "graph_risk": "Proximity to a known-risk network",
    "new_device": "New device for this account",
    "off_hours": "Unusual transaction hour",
    "counterparty_risk": "Counterparty risk signal",
    "impossible_travel": "Impossible travel pattern",
}


def reason_codes(features: dict[str, Any], probability: float, top_k: int = 5) -> list[dict[str, Any]]:
    candidates: list[tuple[str, float]] = [
        ("velocity_1h", min(float(features.get("velocity_1h", 0)) / 10, 1) * 0.92),
        ("velocity_24h", min(float(features.get("velocity_24h", 0)) / 25, 1) * 0.54),
        ("amount_zscore", min(max(float(features.get("amount_zscore", 0)) / 4, 0), 1) * 0.78),
        ("device_sharing_degree", min(float(features.get("device_sharing_degree", 0)) / 8, 1) * 0.72),
        ("graph_risk", float(features.get("graph_risk", 0)) * 0.88),
        ("new_device", float(bool(features.get("new_device"))) * 0.48),
        ("off_hours", float(features.get("off_hours", 0)) * 0.34),
        ("counterparty_risk", float(features.get("counterparty_risk", 0)) * 0.66),
        ("impossible_travel", float(bool(features.get("impossible_travel"))) * 0.91),
    ]
    ordered = sorted(candidates, key=lambda item: item[1], reverse=True)
    return [
        {
            "code": key.upper(),
            "label": _REASON_LABELS[key],
            "contribution": round(value, 3),
            "direction": "increases_risk" if value >= 0.08 else "decreases_risk",
        }
        for key, value in ordered[:top_k]
        if value > 0.02
    ]
