from __future__ import annotations

from datetime import datetime, timedelta, timezone
from random import Random
from typing import Any


def generate_smurfing(accounts: list[str], count: int = 12, seed: int = 183) -> list[dict[str, Any]]:
    rng = Random(seed)
    now = datetime.now(timezone.utc)
    return [{"id": f"tx-smurf-{idx:04d}", "account_id": accounts[idx % len(accounts)], "counterparty_id": accounts[(idx + 1) % len(accounts)], "amount": round(rng.uniform(420, 2400), 2), "currency": "USD", "channel": "transfer", "ts": (now - timedelta(minutes=count - idx)).isoformat(), "labels": ["smurfing", "laundering"]} for idx in range(count)]


def generate_layering(accounts: list[str], hops: int = 5, seed: int = 184) -> list[dict[str, Any]]:
    rng = Random(seed)
    now = datetime.now(timezone.utc)
    return [{"id": f"tx-layer-{idx:04d}", "account_id": accounts[idx % len(accounts)], "counterparty_id": accounts[(idx + 1) % len(accounts)], "amount": round(rng.uniform(7000, 19000), 2), "currency": "USD", "channel": "transfer", "ts": (now - timedelta(minutes=hops - idx)).isoformat(), "labels": ["layering", "laundering"]} for idx in range(hops)]


def generate_round_tripping(accounts: list[str], amount: float = 26000) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    return [{"id": f"tx-round-{idx:04d}", "account_id": accounts[idx % len(accounts)], "counterparty_id": accounts[(idx + 1) % len(accounts)], "amount": round(amount * (1 - idx * .03), 2), "currency": "USD", "channel": "transfer", "ts": (now - timedelta(minutes=3 - idx)).isoformat(), "labels": ["round_tripping", "laundering"]} for idx in range(4)]
