from __future__ import annotations

from typing import Any

from .schemas import Transaction


def transaction_record(payload: Transaction) -> dict[str, Any]:
    """Normalized persistence shape; platform API owns the SQL transaction in the demo."""
    return {"id": payload.id, "account_id": payload.account_id, "amount": payload.amount, "currency": payload.currency.upper(), "channel": payload.channel, "ts": payload.ts.isoformat(), "entity_keys": [payload.device_id, payload.ip_id, payload.merchant_id]}
