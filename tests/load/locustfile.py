from locust import HttpUser, between, task


class ScoringUser(HttpUser):
    wait_time = between(0.01, 0.05)

    @task
    def score_payment(self) -> None:
        self.client.post("/api/v1/score", json={"account_id": "load-acct-1", "amount": 84.50, "currency": "USD", "channel": "card", "merchant_id": "merchant-load", "device_id": "device-load", "ip_id": "ip-load"}, name="POST /api/v1/score")
