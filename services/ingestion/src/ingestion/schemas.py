from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Transaction(BaseModel):
    id: str
    account_id: str = Field(min_length=1)
    counterparty_id: str | None = None
    merchant_id: str | None = None
    device_id: str | None = None
    ip_id: str | None = None
    amount: float = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    channel: Literal["card", "transfer", "wallet"]
    ts: datetime
    country: str = Field(default="US", min_length=2, max_length=2)

    def validate_business_rules(self) -> list[str]:
        errors: list[str] = []
        if self.currency.upper() != self.currency:
            errors.append("currency must be uppercase ISO-4217")
        if self.channel == "card" and not self.merchant_id:
            errors.append("card transactions require merchant_id")
        return errors
