"""M2 HTTP contract: created vs duplicate, Redis retry, validation, and service auth."""

from __future__ import annotations

import uuid

import fakeredis
import pytest
import redis as redis_lib
from fastapi.testclient import TestClient
from ingestion import config, deps
from ingestion.main import app
from ingestion.persistence import MemoryStore

KEY = {"X-Service-Key": config.SERVICE_KEY}
ACCT = str(uuid.uuid4())


def body(**over):
    payload = {"id": str(uuid.uuid4()), "ts": "2026-09-01T12:00:00Z", "account_id": ACCT, "device_id": str(uuid.uuid4()), "amount": "125.50", "currency": "INR", "channel": "card"}
    payload.update(over)
    return payload


@pytest.fixture()
def wired(monkeypatch):
    store, redis_client = MemoryStore(known_accounts={ACCT}), fakeredis.FakeRedis()
    monkeypatch.setattr(deps, "_store", store)
    monkeypatch.setattr(deps, "_redis", redis_client)
    with TestClient(app) as client:
        yield client, store, redis_client


def test_created_then_duplicate(wired):
    client, store, redis_client = wired
    payload = body()
    first = client.post("/api/v1/transactions", json=payload, headers=KEY)
    assert first.status_code == 201
    assert first.json() == {"id": payload["id"], "decision": None, "duplicate": False}
    again = client.post("/api/v1/transactions", json=payload, headers=KEY)
    assert again.status_code == 200 and again.json()["duplicate"] is True
    assert redis_client.zcard(f"vel:acct:{ACCT}:1h") == 1
    assert sum(store.edges.values()) == 1


def test_retry_after_redis_outage_completes_once(wired, monkeypatch):
    client, _store, redis_client = wired

    class Down:
        def register_script(self, _script):
            def boom(**_kwargs):
                raise redis_lib.ConnectionError("down")

            return boom

    payload = body()
    monkeypatch.setattr(deps, "_redis", Down())
    assert client.post("/api/v1/transactions", json=payload, headers=KEY).status_code == 503
    monkeypatch.setattr(deps, "_redis", redis_client)
    retry = client.post("/api/v1/transactions", json=payload, headers=KEY)
    assert retry.status_code == 200 and retry.json()["duplicate"] is True
    assert redis_client.zcard(f"vel:acct:{ACCT}:1h") == 1


@pytest.mark.parametrize("bad", [{"amount": "10.123"}, {"amount": "-5"}, {"currency": "inr"}, {"channel": "cash"}, {"ts": "2026-09-01T12:00:00"}])
def test_validation(wired, bad):
    client, *_ = wired
    assert client.post("/api/v1/transactions", json=body(**bad), headers=KEY).status_code == 422


def test_unknown_account_is_422(wired):
    client, *_ = wired
    response = client.post("/api/v1/transactions", json=body(account_id=str(uuid.uuid4())), headers=KEY)
    assert response.status_code == 422 and "unknown entity" in response.json()["detail"]


def test_service_key_and_probes(wired):
    client, *_ = wired
    assert client.post("/api/v1/transactions", json=body()).status_code == 401
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/ready").json()["status"] == "ready"
    assert b"af_transactions_total" in client.get("/metrics").content
