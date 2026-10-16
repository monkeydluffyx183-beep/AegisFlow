"""Hourly entity-graph feature job.

The graph is undirected for relationship proximity: a ring shares devices regardless of
edge direction. Edge weight means link strength for PageRank, never hop distance. Each run
publishes Redis ``gfeat:acct:*`` hashes and writes a point-in-time PostgreSQL snapshot.
"""

from __future__ import annotations

import argparse
import os
import time
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

import networkx as nx
import pandas as pd

from . import definitions as D

PREFIX = {"account": "acct", "device": "dev", "ip": "ip", "merchant": "mer"}
EDGES_SQL = "SELECT src_type, src_id, dst_type, dst_id, weight FROM entity_edges"
FRAUD_SQL = "SELECT entity_id FROM known_fraud_entities WHERE entity_type = 'account' AND confirmed_at <= %s"
SNAP_SQL = """
INSERT INTO graph_feature_snapshots (entity_id, computed_at, component_size, dist_to_fraud, risk_rank)
VALUES (%s, %s, %s, %s, %s)
"""


def node(entity_type: str, entity_id: object) -> str:
    return f"{PREFIX.get(entity_type, entity_type)}:{entity_id}"


def build_graph(edges: Iterable[tuple[str, object, str, object, float]]) -> nx.Graph:
    graph = nx.Graph()
    for src_type, src_id, dst_type, dst_id, weight in edges:
        source, target = node(src_type, src_id), node(dst_type, dst_id)
        strength = float(weight or 1.0)
        if graph.has_edge(source, target):
            graph[source][target]["weight"] += strength
        else:
            graph.add_edge(source, target, weight=strength)
    return graph


def compute(graph: nx.Graph, fraud_accounts: Iterable[object]) -> pd.DataFrame:
    accounts = [item for item in graph if item.startswith("acct:")]
    component_size: dict[str, int] = {}
    for component in nx.connected_components(graph):
        for item in component:
            component_size[item] = len(component)
    sources = [node("account", account) for account in fraud_accounts if node("account", account) in graph]
    distances: dict[str, int] = {}
    ranks: dict[str, float] = {}
    if sources:
        # One edge is one hop. Weight is strength, not distance.
        distances = dict(nx.multi_source_dijkstra_path_length(graph, sources, weight=lambda _u, _v, _data: 1))
        ranks = nx.pagerank(graph, alpha=0.85, personalization={source: 1.0 for source in sources}, weight="weight")
    return pd.DataFrame(
        {
            "entity_id": [account.split(":", 1)[1] for account in accounts],
            "component_size": [int(component_size[account]) for account in accounts],
            "dist_to_fraud": [int(distances[account]) if account in distances else -1 for account in accounts],
            "risk_rank": [float(ranks.get(account, 0.0)) for account in accounts],
        }
    )


def publish(connection: Any, redis_client: Any, features: pd.DataFrame, computed_at: datetime) -> None:
    with connection.cursor() as cursor:
        cursor.executemany(SNAP_SQL, [(row.entity_id, computed_at, row.component_size, row.dist_to_fraud, row.risk_rank) for row in features.itertuples(index=False)])
    connection.commit()
    pipeline = redis_client.pipeline(transaction=False)
    for row in features.itertuples(index=False):
        key = f"gfeat:acct:{row.entity_id}"
        pipeline.hset(key, mapping={"component_size": row.component_size, "dist_to_fraud": row.dist_to_fraud, "risk_rank": repr(row.risk_rank), "computed_at": computed_at.isoformat()})
        pipeline.expire(key, D.GRAPH_TTL_S)
    pipeline.execute()


def run_once(connection: Any, redis_client: Any) -> int:
    now = datetime.now(UTC)
    graph = build_graph(connection.execute(EDGES_SQL).fetchall())
    fraud = [row[0] for row in connection.execute(FRAUD_SQL, (now,)).fetchall()]
    features = compute(graph, fraud)
    publish(connection, redis_client, features, now)
    return len(features)


def compute_graph_features(edges: Iterable[dict[str, Any]], known_fraud: set[str]) -> dict[str, dict[str, float]]:
    """Compatibility adapter for M1 callers that used dictionary edges."""
    tuples = [(edge.get("src_type", "account"), edge["src_id"], edge.get("dst_type", "account"), edge["dst_id"], edge.get("weight", 1.0)) for edge in edges]
    result = compute(build_graph(tuples), known_fraud)
    return {str(row.entity_id): {"component_size": float(row.component_size), "distance_to_known_fraud": float(row.dist_to_fraud), "risk_propagation": float(row.risk_rank), "pagerank_proxy": float(row.risk_rank)} for row in result.itertuples(index=False)}


def main() -> None:
    import psycopg
    import redis

    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval-s", type=int, default=3_600)
    args = parser.parse_args()
    dsn = os.getenv("DATABASE_URL", "postgresql+psycopg://aegis:aegis_dev_2026@localhost:5432/aegisflow").replace("postgresql+psycopg://", "postgresql://", 1)
    redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    while True:
        started = time.monotonic()
        try:
            with psycopg.connect(dsn) as connection:
                print(f"graph features for {run_once(connection, redis_client)} accounts", flush=True)
        except Exception as exc:  # noqa: BLE001 - the hourly job reports and retries on the next tick.
            print(f"graph pass failed: {exc}", flush=True)
        if args.once:
            break
        time.sleep(max(0, args.interval_s - (time.monotonic() - started)))


if __name__ == "__main__":
    main()
