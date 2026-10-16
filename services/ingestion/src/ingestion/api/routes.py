"""HTTP contract for M2 ingestion: validate, persist, then atomically update Redis."""

from __future__ import annotations

import secrets

import redis as redis_lib
from fastapi import APIRouter, Depends, Header, HTTPException, Response
from loguru import logger
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from .. import config, deps
from ..online_features import update
from ..persistence import UnknownEntity
from ..schemas import TransactionIn, TransactionOut

router = APIRouter()
TXNS = Counter("af_transactions_total", "Transactions received", ["result"])
FEATURE_SECONDS = Histogram("af_online_feature_seconds", "Atomic online feature update latency")


def require_service_key(x_service_key: str | None = Header(default=None)) -> None:
    if x_service_key is None or not secrets.compare_digest(x_service_key, config.SERVICE_KEY):
        raise HTTPException(401, "invalid service key")


@router.post("/api/v1/transactions", response_model=TransactionOut, dependencies=[Depends(require_service_key)])
def post_transaction(transaction: TransactionIn, response: Response) -> TransactionOut:
    try:
        inserted = deps.store().store(transaction)
    except UnknownEntity as exc:
        TXNS.labels("unknown_entity").inc()
        raise HTTPException(422, f"unknown entity: {exc}") from None
    try:
        with FEATURE_SECONDS.time():
            update(deps.redis_client(), transaction.feature_input())
    except redis_lib.RedisError as exc:
        TXNS.labels("features_pending").inc()
        logger.error("online feature update failed for {}: {}", transaction.id, exc)
        raise HTTPException(503, "stored; online features pending - retry the same request") from None
    TXNS.labels("created" if inserted else "duplicate").inc()
    response.status_code = 201 if inserted else 200
    return TransactionOut(id=transaction.id, duplicate=not inserted)


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def ready() -> dict[str, object]:
    checks: dict[str, bool] = {}
    for name, probe in (("database", lambda: deps.store().ping()), ("redis", lambda: bool(deps.redis_client().ping()))):
        try:
            checks[name] = bool(probe())
        except Exception:
            checks[name] = False
    if not all(checks.values()):
        raise HTTPException(503, detail=checks)
    return {"status": "ready", **checks}


@router.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
