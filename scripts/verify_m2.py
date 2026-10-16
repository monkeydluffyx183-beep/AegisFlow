#!/usr/bin/env python3
"""Offline, online, API-contract, and graph checks for the M2 release gate.

The real Redis check is opt-in via ``PARITY_REDIS_URL``. Docker/PostgreSQL verification is
kept separate because this script must be runnable on a laptop with only Python packages.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "ml" / "src", ROOT / "services" / "ingestion" / "src", ROOT):
    sys.path.insert(0, str(path))

import fakeredis
import pandas as pd
from aegis_ml.features import definitions as D
from aegis_ml.features.graph_features import build_graph, compute
from aegis_ml.features.offline import build, prepare
from ingestion.online_features import update


def verify_client(name: str, client, transactions: pd.DataFrame) -> None:
    offline = build(transactions).set_index("id")[D.FEATURE_LIST]
    rows = {}
    for tx in prepare(transactions).itertuples(index=False):
        rows[tx.id] = update(client, {"id": tx.id, "ts": tx.ts.to_pydatetime(), "account_id": tx.account_id, "amount_minor": int(tx.amount_minor), "device_id": tx.device_id, "ip_id": tx.ip_id})
    online = pd.DataFrame.from_dict(rows, orient="index")[D.FEATURE_LIST]
    pd.testing.assert_frame_equal(offline.loc[online.index].astype(float), online.astype(float), check_exact=True)
    print(f"{name}: exact parity for {len(online):,} transactions and {len(D.FEATURE_LIST)} features")


def main() -> int:
    if len(D.FEATURE_LIST) != 19 or len(set(D.FEATURE_LIST)) != 19:
        raise AssertionError(f"expected 19 unique canonical features, got {D.FEATURE_LIST}")
    if not D.FEATURE_SET_VERSION:
        raise AssertionError("missing feature set version")
    from tests.m2.support import stream

    transactions = stream(5_000)
    verify_client("fakeredis", fakeredis.FakeRedis(), transactions)
    url = os.getenv("PARITY_REDIS_URL")
    if url:
        import redis

        client = redis.Redis.from_url(url)
        client.flushdb()
        verify_client("redis", client, transactions)
    graph = compute(build_graph([("account", "A", "device", "D", 1), ("account", "B", "device", "D", 1)]), ["A"])
    assert graph.loc[graph.entity_id == "B", "dist_to_fraud"].item() == 2
    print(f"graph: {len(graph)} account features computed")
    print(f"feature set: {D.FEATURE_SET_VERSION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
