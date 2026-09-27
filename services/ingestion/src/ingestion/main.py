from __future__ import annotations

"""Thin ingestion service entrypoint for deployments that split the gateway from the API."""

from fastapi import FastAPI, HTTPException

from .online_features import redis_keys
from .schemas import Transaction

app = FastAPI(title="AegisFlow Ingestion", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ingestion"}


@app.post("/transactions", status_code=202)
def accept_transaction(transaction: Transaction) -> dict[str, object]:
    errors = transaction.validate_business_rules()
    if errors:
        raise HTTPException(status_code=422, detail=errors)
    feature_key, velocity_key = redis_keys(transaction.account_id)
    return {"accepted": True, "transaction_id": transaction.id, "online_feature_keys": [feature_key, velocity_key], "outbox_event": "txn.received"}
