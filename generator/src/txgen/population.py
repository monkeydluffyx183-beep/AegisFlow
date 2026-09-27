from __future__ import annotations

from dataclasses import dataclass
from random import Random


@dataclass(frozen=True)
class Account:
    id: str
    avg_amount: float
    amount_std: float
    home_country: str
    device_id: str


@dataclass(frozen=True)
class Device:
    id: str
    fingerprint: str


def build_population(count: int = 250, devices: int = 180, seed: int = 183) -> tuple[list[Account], list[Device]]:
    rng = Random(seed)
    device_rows = [Device(f"dev-{idx:05d}", f"fp-{rng.getrandbits(64):016x}") for idx in range(devices)]
    accounts: list[Account] = []
    for idx in range(count):
        avg = round(max(20, rng.lognormvariate(5.1, 0.7)), 2)
        device = device_rows[idx % devices]
        accounts.append(Account(f"acct-gen-{idx:05d}", avg, round(max(15, avg * rng.uniform(.25, .75)), 2), rng.choice(["US", "GB", "IN", "SG"]), device.id))
    return accounts, device_rows
