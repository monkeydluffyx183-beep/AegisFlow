"""THE M2 contract: Lua and offline features match every row/column exactly."""

from __future__ import annotations

import os

import fakeredis
import pandas as pd
import pytest
from aegis_ml.features import definitions as D
from aegis_ml.features.offline import build, prepare
from ingestion.online_features import update

from tests.m2.support import stream


def _redis_clients():
    clients = [("fakeredis", fakeredis.FakeRedis())]
    if os.getenv("PARITY_REDIS_URL"):
        import redis

        client = redis.Redis.from_url(os.environ["PARITY_REDIS_URL"])
        client.flushdb()
        clients.append(("redis", client))
    return clients


@pytest.mark.parametrize("name,redis_client", _redis_clients())
def test_online_equals_offline_for_every_transaction(name, redis_client):
    transactions = stream()
    offline = build(transactions).set_index("id")[D.FEATURE_LIST]
    online = {}
    for transaction in prepare(transactions).itertuples(index=False):
        online[transaction.id] = update(
            redis_client,
            {
                "id": transaction.id,
                "ts": transaction.ts.to_pydatetime(),
                "account_id": transaction.account_id,
                "amount_minor": int(transaction.amount_minor),
                "device_id": transaction.device_id,
                "ip_id": transaction.ip_id,
            },
        )
    online_frame = pd.DataFrame.from_dict(online, orient="index")[D.FEATURE_LIST]
    pd.testing.assert_frame_equal(offline.loc[online_frame.index].astype(float), online_frame.astype(float), check_exact=True)
    if name == "redis":
        redis_client.flushdb()


def test_stream_really_exercises_edges() -> None:
    frame = prepare(stream())
    assert frame["t"].duplicated().any()
    assert frame["device_id"].isna().any()
    gaps = frame["t"].diff()
    assert (gaps == 60).any() and (gaps == 3_600).any()
