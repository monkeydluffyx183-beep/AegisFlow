"""Against a migrated PostgreSQL and Redis stack; skipped without DATABASE_URL.

The fixture uses the repository's generic ``entities`` table (M1), creates an account/device
ring, and cleans every row it owns. It is deliberately separate from fakeredis parity tests.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="requires a migrated PostgreSQL database")

import psycopg
import redis
from aegis_ml.features import graph_features as graph
from ingestion.persistence import PgStore, UnknownEntity
from ingestion.schemas import TransactionIn
from sqlalchemy import create_engine


@pytest.fixture()
def conn():
    dsn = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://", 1)
    with psycopg.connect(dsn) as connection:
        yield connection


@pytest.fixture()
def ring(conn):
    accounts = [str(uuid.uuid4()) for _ in range(3)]
    device = str(uuid.uuid4())
    for account in accounts:
        conn.execute("INSERT INTO entities (id, entity_type, label, risk_tier) VALUES (%s, 'account', %s, 'standard')", (account, account))
    conn.execute("INSERT INTO entities (id, entity_type, label, risk_tier) VALUES (%s, 'device', 'integration device', 'standard')", (device,))
    conn.execute("INSERT INTO known_fraud_entities VALUES ('account', %s, now() - interval '1 day', 'it_test')", (accounts[0],))
    conn.commit()
    yield accounts, device
    ids = accounts + [device]
    conn.execute("DELETE FROM graph_feature_snapshots WHERE entity_id = ANY(%s)", (accounts,))
    conn.execute("DELETE FROM entity_edges WHERE src_id = ANY(%s) OR dst_id = ANY(%s)", (accounts, accounts))
    conn.execute("DELETE FROM transactions WHERE account_id = ANY(%s)", (accounts,))
    conn.execute("DELETE FROM known_fraud_entities WHERE source = 'it_test'")
    conn.execute("DELETE FROM entities WHERE id = ANY(%s)", (ids,))
    conn.commit()


def txn(account: str, device: str, minute: int) -> TransactionIn:
    return TransactionIn(id=uuid.uuid4(), account_id=account, device_id=device, ts=datetime(2026, 9, 1, 12, minute, tzinfo=UTC), amount=Decimal("10.00"), currency="INR", channel="card")


def test_store_is_idempotent_and_upserts_edges(conn, ring):
    (account, _b, _c), device = ring
    store = PgStore(create_engine(os.environ["DATABASE_URL"]))
    first = txn(account, device, 0)
    assert store.store(first) is True and store.store(first) is False
    assert store.store(txn(account, device, 1)) is True
    weight = conn.execute("SELECT weight FROM entity_edges WHERE src_id = %s AND dst_id = %s", (account, device)).fetchone()[0]
    assert weight == 2
    with pytest.raises(UnknownEntity):
        store.store(txn(str(uuid.uuid4()), device, 2))


def test_graph_job_publishes_snapshots_and_redis(conn, ring):
    (account_a, account_b, account_c), device = ring
    store = PgStore(create_engine(os.environ["DATABASE_URL"]))
    for index, account in enumerate((account_a, account_b, account_c)):
        store.store(txn(account, device, 10 + index))
    redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    graph.run_once(conn, redis_client)
    row = conn.execute("SELECT component_size, dist_to_fraud FROM graph_feature_snapshots WHERE entity_id = %s ORDER BY computed_at DESC LIMIT 1", (account_b,)).fetchone()
    assert row[0] >= 4 and row[1] == 2
    assert redis_client.hget(f"gfeat:acct:{account_b}", "dist_to_fraud") == b"2"
    assert 0 < redis_client.ttl(f"gfeat:acct:{account_b}") <= 7_200
    redis_client.delete(*[f"gfeat:acct:{account}" for account in (account_a, account_b, account_c)])


def test_unique_edge_index_exists(conn):
    assert conn.execute("SELECT 1 FROM pg_indexes WHERE indexname = 'uq_entity_edges_key'").fetchone() is not None
