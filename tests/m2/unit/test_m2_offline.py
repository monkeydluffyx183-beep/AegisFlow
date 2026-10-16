"""Hand-computed boundaries, ties, include-current, profile order, and graph cutoff."""

from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest
from aegis_ml.features import definitions as D
from aegis_ml.features.offline import attach_graph, build

T = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
A, B, DEV = "a", "b", "d1"


def txn(index: int, seconds: int, account: str, minor: int, device: str | None = DEV) -> dict[str, object]:
    return {"id": f"t{index}", "ts": T + timedelta(seconds=seconds), "account_id": account, "amount_minor": minor, "device_id": device, "ip_id": None}


def frame() -> pd.DataFrame:
    return pd.DataFrame([txn(1, 0, A, 1000), txn(2, 30, A, 2000), txn(3, 30, A, 3000), txn(4, 60, A, 4000), txn(5, 61, B, 500), txn(6, 120, A, 1000, None)])


def test_velocity_edges_and_ties() -> None:
    features = build(frame()).set_index("id")
    assert features.loc["t3", "txn_count_1m"] == 3
    assert features.loc["t2", "txn_count_1m"] == 2
    assert features.loc["t4", "txn_count_1m"] == 3
    assert features.loc["t4", "amount_sum_minor_1m"] == 9000
    assert features.loc["t6", "txn_count_1m"] == 1


def test_sharing_and_distinct() -> None:
    features = build(frame()).set_index("id")
    assert features.loc["t5", "device_accounts_7d"] == 2
    assert features.loc["t6", "device_accounts_7d"] == 0
    assert features.loc["t6", "distinct_devices_24h"] == 1


def test_zscore_uses_profile_before_current() -> None:
    features = build(frame()).set_index("id")
    assert features.loc["t1", "amount_zscore"] == 0.0
    assert features.loc["t2", "amount_zscore"] == 0.0
    assert features.loc["t3", "amount_zscore"] == pytest.approx((30 - 15) / (50.0**0.5))
    assert features.loc["t1", "seconds_since_prev"] == -1.0
    assert features.loc["t4", "seconds_since_prev"] == 30.0


def test_graph_join_is_point_in_time() -> None:
    snapshots = pd.DataFrame([{"entity_id": A, "computed_at": T + timedelta(seconds=45), "component_size": 4, "dist_to_fraud": 2, "risk_rank": 0.1}])
    features = attach_graph(build(frame()), snapshots).set_index("id")
    assert features.loc["t2", "graph_component_size"] == 1.0
    assert features.loc["t4", "graph_component_size"] == 4.0
    assert features.loc["t5", "graph_dist_to_fraud"] == -1.0
    assert list(features.columns[2:]) == D.FEATURE_LIST
