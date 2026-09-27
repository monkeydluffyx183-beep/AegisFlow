from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..online_features import redis_keys
from ..persistence import transaction_record
from ..schemas import Transaction

router = APIRouter(prefix="/api/v1", tags=["ingestion"])


@router.post("/transactions", status_code=202)
def ingest(payload: Transaction) -> dict[str, object]:
    errors = payload.validate_business_rules()
    if errors:
        raise HTTPException(422, errors)
    return {"accepted": True, "transaction": transaction_record(payload), "feature_keys": redis_keys(payload.account_id), "outbox": "txn.received"}
