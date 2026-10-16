from datetime import datetime, timedelta, timezone

from aegis_ml.features.definitions import feature_names
from aegis_ml.features.offline import compute_features
from scoring.engine import ScoringEngine
from scoring.schemas import ScoreRequest


def test_offline_features_are_point_in_time_ordered() -> None:
    now = datetime.now(timezone.utc)
    rows = [
        {"id": "later", "account_id": "a", "device_id": "d", "amount": 9999, "ts": now + timedelta(minutes=1), "label": 1},
        {"id": "first", "account_id": "a", "device_id": "d", "amount": 10, "ts": now, "label": 0},
    ]
    output = compute_features(rows)
    assert [row["id"] for row in output] == ["first", "later"]
    assert output[0]["velocity_1h"] == 0  # M1 compatibility wrapper excludes current row
    assert set(feature_names()).issubset(output[0])


def test_online_reader_exposes_same_feature_names() -> None:
    engine = ScoringEngine()
    result = engine.score(ScoreRequest(id="tx", account_id="a", amount=50, channel="card"))
    expected = {"velocity_1h", "velocity_24h", "amount_zscore", "device_sharing_degree", "graph_risk", "new_device", "off_hours"}
    assert expected.issubset(result.features)
