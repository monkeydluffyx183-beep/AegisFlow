from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Thresholds:
    review: float = 0.45
    decline: float = 0.76


def clamp(value: float, low: float = 0.001, high: float = 0.999) -> float:
    return max(low, min(high, value))


def model_probability(features: dict[str, Any], challenger: bool = False) -> float:
    """Small deterministic stand-in for the calibrated XGBoost runtime.

    The production seam is deliberately explicit: this function consumes the same feature
    vector the online/offline definition module emits and can be replaced by an MLflow
    predictor without changing the decision contract.
    """

    score = -2.55
    score += min(float(features.get("amount_zscore", 0)), 5) * 0.30
    score += min(float(features.get("velocity_1h", 0)), 20) * 0.095
    score += min(float(features.get("velocity_24h", 0)), 50) * 0.018
    score += float(features.get("device_sharing_degree", 0)) * 0.16
    score += float(features.get("graph_risk", 0)) * 1.10
    score += float(features.get("off_hours", 0)) * 0.25
    score += float(features.get("new_device", 0)) * 0.35
    score += float(features.get("counterparty_risk", 0)) * 0.75
    if challenger:
        score += float(features.get("graph_risk", 0)) * 0.12
        score -= float(features.get("account_history", 0)) * 0.03
    # Stable logistic without pulling a heavyweight model into the demo runtime.
    import math

    return clamp(1 / (1 + math.exp(-score)))


def choose_decision(probability: float, hits: list[Any], thresholds: Thresholds) -> str:
    if any(getattr(hit, "action", "") == "decline" for hit in hits):
        return "decline"
    if probability >= thresholds.decline:
        return "decline"
    if probability >= thresholds.review or hits:
        return "review"
    return "approve"
