from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ScoringConfig:
    review_threshold: float = float(os.getenv("REVIEW_THRESHOLD", "0.45"))
    decline_threshold: float = float(os.getenv("DECLINE_THRESHOLD", "0.76"))
    model_version: str = os.getenv("MODEL_VERSION", "fraud-champion-2026.09")
    max_reason_codes: int = 5
    latency_slo_ms: float = 100.0
