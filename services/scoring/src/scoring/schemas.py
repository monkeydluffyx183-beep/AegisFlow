from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ScoreRequest(BaseModel):
    """The stable contract between a payment gateway and the scorer."""

    model_config = ConfigDict(extra="allow")

    id: str | None = None
    account_id: str = Field(min_length=1, max_length=96)
    counterparty_id: str | None = None
    merchant_id: str | None = None
    device_id: str | None = None
    ip_id: str | None = None
    amount: float = Field(gt=0, le=10_000_000)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    channel: Literal["card", "transfer", "wallet"] = "card"
    country: str = Field(default="US", min_length=2, max_length=2)
    geo_lat: float | None = Field(default=None, ge=-90, le=90)
    geo_lon: float | None = Field(default=None, ge=-180, le=180)
    ts: datetime = Field(default_factory=lambda: datetime.now(UTC))
    labels: list[str] = Field(default_factory=list)


class ReasonCode(BaseModel):
    code: str
    label: str
    contribution: float
    direction: Literal["increases_risk", "decreases_risk"] = "increases_risk"


class RuleHit(BaseModel):
    rule_id: str
    label: str
    severity: Literal["low", "medium", "high", "critical"]
    action: Literal["review", "decline"]
    detail: str


class DecisionResult(BaseModel):
    transaction_id: str
    decision: Literal["approve", "review", "decline"]
    score: float
    calibrated_prob: float
    reason_codes: list[ReasonCode]
    rule_hits: list[RuleHit]
    features: dict[str, float | int | bool | str]
    model_version: str
    challenger: dict[str, float | bool | str]
    latency_ms: float
    degraded: bool = False
    feature_store_hit: bool = True
