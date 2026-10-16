"""Deterministic 5,000-row replay stream for the exact online/offline parity proof."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd

T0 = datetime(2026, 9, 1, tzinfo=UTC)
NS = uuid.UUID("0b6c6f2e-2d8a-4f53-9a51-3c1d2b7e8f90")


def stream(n: int = 5_000, accounts: int = 300, devices: int = 150, ips: int = 100, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    account_ids = [str(uuid.uuid5(NS, f"acct-{index}")) for index in range(accounts)]
    device_ids = [str(uuid.uuid5(NS, f"dev-{index}")) for index in range(devices)]
    ip_ids = [str(uuid.uuid5(NS, f"ip-{index}")) for index in range(ips)]
    gaps = rng.choice([0, 0, 1, 5, 30, 59, 60, 61, 600, 3_600, 86_400], size=n)
    jitter = rng.integers(0, 1_000_000, size=n) / 1e6 * (rng.random(n) < 0.3)
    seconds = np.cumsum(gaps) + jitter
    rows = []
    for index in range(n):
        rows.append(
            {
                "id": str(uuid.uuid5(NS, f"txn-{seed}-{index}")),
                "ts": T0 + timedelta(microseconds=round(seconds[index] * 1e6)),
                "account_id": account_ids[int(rng.zipf(1.6)) % accounts],
                "amount_minor": int(rng.integers(100, 500_000)),
                "device_id": None if rng.random() < 0.15 else device_ids[int(rng.integers(devices))],
                "ip_id": None if rng.random() < 0.10 else ip_ids[int(rng.integers(ips))],
            }
        )
    return pd.DataFrame(rows)
