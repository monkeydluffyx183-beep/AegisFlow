"""M2 ingestion wire contract.

Money is validated as Decimal with two decimal places and identifiers are UUIDs so the
persistence layer can enforce the entity foreign-key contract. Timestamps must carry a
zone because the feature store is event-time based.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class TransactionIn(BaseModel):
    id: UUID
    ts: datetime
    account_id: UUID
    counterparty_id: UUID | None = None
    merchant_id: UUID | None = None
    device_id: UUID | None = None
    ip_id: UUID | None = None
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    channel: Literal["card", "transfer", "wallet"]

    @field_validator("ts")
    @classmethod
    def timestamp_is_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("ts must carry a timezone")
        return value

    def feature_input(self) -> dict[str, object]:
        from aegis_ml.features.definitions import amount_minor

        return {
            "id": str(self.id),
            "ts": self.ts,
            "account_id": str(self.account_id),
            "amount_minor": amount_minor(self.amount),
            "device_id": str(self.device_id) if self.device_id else None,
            "ip_id": str(self.ip_id) if self.ip_id else None,
        }


class TransactionOut(BaseModel):
    id: UUID
    decision: str | None = None  # populated by M4's scoring service
    duplicate: bool = False
