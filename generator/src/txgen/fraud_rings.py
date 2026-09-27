from __future__ import annotations

from random import Random
from typing import Any


def inject_ring(account_ids: list[str], shared_device: str = "dev-ring-shared", count: int = 20, seed: int = 183) -> list[dict[str, Any]]:
    rng = Random(seed)
    return [{"account_id": account_id, "device_id": shared_device, "ip_id": "ip-ring-01", "amount": round(rng.uniform(80, 950), 2), "labels": ["fraud_ring"], "ring_id": "ring-demo-01"} for account_id in (account_ids * ((count // len(account_ids)) + 1))[:count]]
