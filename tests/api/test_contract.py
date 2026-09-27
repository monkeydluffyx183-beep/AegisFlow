from aegisflow_platform.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health_and_openapi() -> None:
    assert client.get("/health").status_code == 200
    spec = client.get("/openapi.json").json()
    assert "/api/v1/score" in spec["paths"]
    assert "/api/v1/sar/{case_id}/approve" in spec["paths"]


def test_demo_cases_and_score_contract() -> None:
    cases = client.get("/api/v1/cases").json()
    assert cases["count"] >= 1
    response = client.post("/api/v1/score", json={"account_id": "test-contract", "amount": 25, "currency": "USD", "channel": "card", "merchant_id": "merchant-1"})
    assert response.status_code == 200
    payload = response.json()
    assert {"decision", "calibrated_prob", "reason_codes", "latency_ms", "degraded"}.issubset(payload)
    assert len(payload["reason_codes"]) <= 5


def test_analyst_cannot_approve() -> None:
    response = client.post("/api/v1/sar/case_ring_1042/approve", headers={"X-User-Email": "priya@aegisflow.demo", "X-Role": "aml_analyst"}, json={"rationale": "This should be blocked for analyst role."})
    assert response.status_code == 403
