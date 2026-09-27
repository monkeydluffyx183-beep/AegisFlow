from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(32), default="aml_analyst")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Entity(Base):
    __tablename__ = "entities"
    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(24), index=True)
    label: Mapped[str] = mapped_column(String(160))
    risk_tier: Mapped[str] = mapped_column(String(24), default="standard")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class EntityEdge(Base):
    __tablename__ = "entity_edges"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    src_id: Mapped[str] = mapped_column(String(96), index=True)
    dst_id: Mapped[str] = mapped_column(String(96), index=True)
    edge_type: Mapped[str] = mapped_column(String(32), index=True)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Transaction(Base):
    __tablename__ = "transactions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    account_id: Mapped[str] = mapped_column(String(96), index=True)
    counterparty_id: Mapped[str | None] = mapped_column(String(96), nullable=True)
    merchant_id: Mapped[str | None] = mapped_column(String(96), nullable=True)
    device_id: Mapped[str | None] = mapped_column(String(96), nullable=True)
    ip_id: Mapped[str | None] = mapped_column(String(96), nullable=True)
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    channel: Mapped[str] = mapped_column(String(16), default="card")
    country: Mapped[str] = mapped_column(String(2), default="US")
    status: Mapped[str] = mapped_column(String(24), default="received")
    raw: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Decision(Base):
    __tablename__ = "decisions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    transaction_id: Mapped[str] = mapped_column(String(64), ForeignKey("transactions.id"), unique=True, index=True)
    decision: Mapped[str] = mapped_column(String(16), index=True)
    score: Mapped[float] = mapped_column(Float)
    calibrated_prob: Mapped[float] = mapped_column(Float)
    reason_codes: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    rule_hits: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    features: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    model_version: Mapped[str] = mapped_column(String(80))
    challenger: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    latency_ms: Mapped[float] = mapped_column(Float)
    degraded: Mapped[bool] = mapped_column(Boolean, default=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class Case(Base):
    __tablename__ = "cases"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(220))
    priority: Mapped[float] = mapped_column(Float, default=50, index=True)
    status: Mapped[str] = mapped_column(String(24), default="open", index=True)
    assigned_to: Mapped[str | None] = mapped_column(String(64), ForeignKey("users.id"), nullable=True)
    assignee_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    sla_due: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    disposition: Mapped[str | None] = mapped_column(String(24), nullable=True)
    disposition_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    typology: Mapped[str] = mapped_column(String(48), default="network_anomaly")
    account_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Alert(Base):
    __tablename__ = "alerts"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    transaction_id: Mapped[str] = mapped_column(String(64), ForeignKey("transactions.id"), index=True)
    case_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("cases.id"), nullable=True, index=True)
    alert_type: Mapped[str] = mapped_column(String(64))
    severity: Mapped[str] = mapped_column(String(16))
    reason: Mapped[str] = mapped_column(String(220))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class EvidenceItem(Base):
    __tablename__ = "evidence_items"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(64), ForeignKey("cases.id"), index=True)
    kind: Mapped[str] = mapped_column(String(24))
    title: Mapped[str] = mapped_column(String(220))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    source_ref: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_by: Mapped[str] = mapped_column(String(24), default="agent")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SARDraft(Base):
    __tablename__ = "sar_drafts"
    __table_args__ = (UniqueConstraint("case_id", "version", name="uq_sar_case_version"),)
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(64), ForeignKey("cases.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    narrative_md: Mapped[str] = mapped_column(Text)
    citations: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(24), default="draft")
    author: Mapped[str] = mapped_column(String(24), default="agent")
    reviewed_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    review_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    actor_id: Mapped[str] = mapped_column(String(96))
    actor_role: Mapped[str] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(String(96), index=True)
    resource_type: Mapped[str] = mapped_column(String(32))
    resource_id: Mapped[str] = mapped_column(String(96), index=True)
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class ThresholdConfig(Base):
    __tablename__ = "threshold_config"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    review_threshold: Mapped[float] = mapped_column(Float, default=0.45)
    decline_threshold: Mapped[float] = mapped_column(Float, default=0.76)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_by: Mapped[str] = mapped_column(String(96), default="system")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
if settings.database_url.startswith("sqlite"):
    db_path = settings.database_url.replace("sqlite:///", "", 1)
    parent = os.path.dirname(db_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
engine = create_engine(settings.database_url, future=True, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def new_id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:16]}"


def audit(session: Any, actor_id: str, actor_role: str, action: str, resource_type: str, resource_id: str, detail: dict[str, Any] | None = None) -> AuditLog:
    row = AuditLog(id=new_id("aud_"), actor_id=actor_id, actor_role=actor_role, action=action, resource_type=resource_type, resource_id=resource_id, detail=detail or {})
    session.add(row)
    return row
