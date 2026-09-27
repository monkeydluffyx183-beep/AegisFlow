from __future__ import annotations

from datetime import datetime, timedelta, timezone
from random import Random
from typing import Any

from .population import Account


def normal_transaction(account: Account, rng: Random, index: int, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    return {"id": f"tx-gen-{index:08d}", "account_id": account.id, "counterparty_id": f"acct-gen-{rng.randrange(0, 250):05d}", "merchant_id": f"merchant-{rng.randrange(0, 80):04d}", "device_id": account.device_id, "ip_id": f"ip-gen-{rng.randrange(0, 100):04d}", "amount": round(max(1, rng.gauss(account.avg_amount, account.amount_std)), 2), "currency": "USD", "channel": rng.choice(["card", "card", "wallet", "transfer"]), "country": account.home_country, "ts": (now - timedelta(seconds=rng.randrange(0, 3600))).isoformat(), "labels": []}
