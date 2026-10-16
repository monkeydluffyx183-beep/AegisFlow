from types import SimpleNamespace

from scoring.decision import Thresholds, choose_decision, model_probability
from scoring.engine import ScoringEngine
from scoring.rules import evaluate_rules
from scoring.schemas import ScoreRequest


def test_decline_rule_overrides_model_probability() -> None:
    request = SimpleNamespace(amount=50)
    hits = evaluate_rules(request, {"sanctions_hit": True, "velocity_1h": 0})
    assert choose_decision(.04, hits, Thresholds()) == "decline"


def test_engine_returns_top_five_reasons_and_shadow() -> None:
    engine = ScoringEngine()
    engine.seed_account("ring-1", graph_risk=.9, device_sharing_degree=8, avg_amount=100, amount_std=10)
    result = engine.score(ScoreRequest(id="tx-1", account_id="ring-1", amount=1600, device_id="device-new", channel="transfer"))
    assert len(result.reason_codes) <= 5
    assert result.model_version.startswith("fraud-champion")
    assert result.challenger["version"] == "fraud-challenger-graph-v2"
    assert result.latency_ms >= 0


def test_probability_is_bounded() -> None:
    assert 0 < model_probability({}) < 1
    assert 0 < model_probability({"velocity_1h": 100, "graph_risk": 1}) < 1
