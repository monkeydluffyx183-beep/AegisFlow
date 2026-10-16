from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TransactionIn(BaseModel):
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
    ts: datetime | None = None
    labels: list[str] = Field(default_factory=list)


class ScoreRequest(TransactionIn):
    pass


class ScoreResponse(BaseModel):
    transaction_id: str
    decision: str
    score: float
    calibrated_prob: float
    reason_codes: list[dict[str, Any]]
    rule_hits: list[dict[str, Any]]
    features: dict[str, Any]
    model_version: str
    challenger: dict[str, Any]
    latency_ms: float
    degraded: bool
    feature_store_hit: bool


class ThresholdsIn(BaseModel):
    review_t: float = Field(gt=0, lt=1)
    decline_t: float = Field(gt=0, lt=1)


class DispositionIn(BaseModel):
    disposition: Literal["fraud", "not_fraud", "sar_filed"]
    rationale: str = Field(min_length=10, max_length=2000)


class EditDraftIn(BaseModel):
    narrative_md: str = Field(min_length=30, max_length=50_000)
    citations: list[dict[str, Any]] = Field(default_factory=list)


class ApprovalIn(BaseModel):
    rationale: str = Field(min_length=10, max_length=2000)


class LoginIn(BaseModel):
    email: str
    password: str


class UserOut(APIModel):
    id: str
    email: str
    display_name: str
    role: str


class CaseSummary(APIModel):
    id: str
    title: str
    priority: float
    status: str
    assigned_to: str | None
    assignee_name: str | None
    sla_due: datetime
    disposition: str | None
    typology: str
    account_ids: list[str]
    created_at: datetime
    updated_at: datetime | None
    alert_count: int = 0
    evidence_count: int = 0
    risk_score: float = 0


class CaseDetail(CaseSummary):
    alerts: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    drafts: list[dict[str, Any]]
    graph: dict[str, Any]
    audit: list[dict[str, Any]]


class APIError(BaseModel):
    detail: str
