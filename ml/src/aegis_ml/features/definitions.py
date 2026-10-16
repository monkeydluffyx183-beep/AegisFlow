"""Single source of truth for AegisFlow's M2 feature store.

Both the Redis/Lua online path and the point-in-time offline builder import this module.
The ordering and boundary rules here are part of the model contract:

* event time is the transaction's own ``ts`` (never Redis wall-clock time);
* windows are ``(ts - window, ts]`` and include the current transaction;
* ties are ordered by ``(ts, id)``;
* ``amount_zscore`` reads the Welford profile before the current amount is added;
* graph fields are joined from the latest snapshot that existed at transaction time.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

WINDOWS: dict[str, int] = {"1m": 60, "1h": 3_600, "24h": 86_400, "7d": 604_800}
DISTINCT_WINDOW_S = 86_400
SHARE_WINDOW_S = 604_800
KEY_TTL_S = 8 * 86_400
GRAPH_TTL_S = 2 * 3_600


@dataclass(frozen=True)
class Feature:
    name: str
    entity: str
    kind: str
    window_s: int | None
    include_current: bool
    default: float
    source: str


def _velocity() -> list[Feature]:
    output: list[Feature] = []
    for label, window in WINDOWS.items():
        output.append(Feature(f"txn_count_{label}", "account", "count", window, True, 0.0, "lua"))
        output.append(Feature(f"amount_sum_minor_{label}", "account", "sum", window, True, 0.0, "lua"))
    return output


FEATURES: list[Feature] = _velocity() + [
    Feature("distinct_devices_24h", "account", "distinct", DISTINCT_WINDOW_S, True, 0.0, "lua"),
    Feature("distinct_ips_24h", "account", "distinct", DISTINCT_WINDOW_S, True, 0.0, "lua"),
    Feature("device_accounts_7d", "device", "distinct", SHARE_WINDOW_S, True, 0.0, "lua"),
    Feature("ip_accounts_7d", "ip", "distinct", SHARE_WINDOW_S, True, 0.0, "lua"),
    Feature("amount_zscore", "account", "zscore", None, False, 0.0, "lua"),
    Feature("seconds_since_prev", "account", "recency", None, False, -1.0, "lua"),
    Feature("hour_of_day", "account", "calendar", None, True, 0.0, "calendar"),
    Feature("day_of_week", "account", "calendar", None, True, 0.0, "calendar"),
    Feature("graph_component_size", "account", "graph", None, False, 1.0, "graph"),
    Feature("graph_dist_to_fraud", "account", "graph", None, False, -1.0, "graph"),
    Feature("graph_risk_rank", "account", "graph", None, False, 0.0, "graph"),
]
FEATURE_LIST = [feature.name for feature in FEATURES]
BY_NAME = {feature.name: feature for feature in FEATURES}
LUA_OUTPUTS = [feature.name for feature in FEATURES if feature.source == "lua"]
GRAPH_FIELDS = {
    "graph_component_size": "component_size",
    "graph_dist_to_fraud": "dist_to_fraud",
    "graph_risk_rank": "risk_rank",
}
FEATURE_SET_VERSION = hashlib.sha256(
    json.dumps([asdict(feature) for feature in FEATURES] + [WINDOWS, DISTINCT_WINDOW_S, SHARE_WINDOW_S], sort_keys=True).encode()
).hexdigest()[:12]
_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)

# Compatibility aliases used by the M1 scorer and older notebooks. M2's canonical names
# remain the 19 names above; aliases are emitted only by ``compute_features``.
LEGACY_ALIASES = {
    "velocity_1h": "txn_count_1h",
    "velocity_24h": "txn_count_24h",
    "device_sharing_degree": "device_accounts_7d",
    "graph_risk": "graph_risk_rank",
}


def epoch_seconds(ts: datetime) -> float:
    if ts.tzinfo is None or ts.utcoffset() is None:
        raise ValueError("feature timestamps must carry a timezone")
    return ((ts.astimezone(UTC) - _EPOCH) // timedelta(microseconds=1)) / 1_000_000


def calendar(ts: datetime) -> dict[str, float]:
    utc = ts.astimezone(UTC)
    return {"hour_of_day": float(utc.hour), "day_of_week": float(utc.weekday())}


def amount_minor(amount: Decimal | float | str) -> int:
    """Convert money to integer minor units before it crosses into Redis/Lua."""
    value = amount if isinstance(amount, Decimal) else Decimal(str(amount))
    return int((value * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def feature_names() -> list[str]:
    return list(FEATURE_LIST)


def defaults() -> dict[str, float]:
    return {feature.name: feature.default for feature in FEATURES}


def feature_spec() -> list[dict[str, object]]:
    return [asdict(feature) for feature in FEATURES]
