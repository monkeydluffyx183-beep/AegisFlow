from casework.correlation import AlertRef, correlate
from casework.priority import priority_score
from investigator.tools.graph_tools import path_to_known_fraud
from investigator.tools.typology_tools import typology_scan


def test_correlation_joins_shared_device() -> None:
    groups = correlate([AlertRef("a1", "acct-1", device_id="dev-shared"), AlertRef("a2", "acct-2", device_id="dev-shared"), AlertRef("a3", "acct-3")])
    assert sorted(map(len, groups)) == [1, 2]


def test_priority_has_typology_premium() -> None:
    base = priority_score(probability=.8, amount=500, severity="high")
    typology = priority_score(probability=.8, amount=500, severity="high", typology_match=True)
    assert typology > base


def test_graph_path_to_known_fraud() -> None:
    result = path_to_known_fraud([{"source": "a", "target": "d"}, {"source": "d", "target": "fraud"}], "a", {"fraud"})
    assert result == {"path": ["a", "d", "fraud"], "hops": 2}


def test_smurfing_detector_returns_supporting_ids() -> None:
    transactions = [{"transaction_id": f"tx-{i}", "account_id": "a", "amount": 100, "ts": str(i)} for i in range(6)]
    finding = typology_scan(transactions)
    assert finding[0]["typology"] == "smurfing"
    assert len(finding[0]["transaction_ids"]) == 6
