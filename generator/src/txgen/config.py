from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GeneratorConfig:
    seed: int = 183
    accounts: int = 250
    devices: int = 180
    merchants: int = 80
    rate: float = 5.0
    endpoint: str = "http://localhost:8000/api/v1/transactions"
