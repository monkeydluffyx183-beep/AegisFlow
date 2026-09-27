from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class FeatureDefinition:
    name: str
    entity: Literal["account", "device", "transaction", "graph"]
    window: str
    aggregation: str
    default: float | int | bool
    description: str
    online_key: str
    extractor: Callable[[dict[str, Any], list[dict[str, Any]]], float | int | bool] | None = None


def _count_window(row: dict[str, Any], history: list[dict[str, Any]], hours: int) -> int:
    ts = row.get("ts")
    if not ts:
        return len(history)
    return sum(1 for item in history if (ts - item.get("ts", ts)).total_seconds() <= hours * 3600 and item.get("account_id") == row.get("account_id"))


FEATURE_DEFINITIONS: tuple[FeatureDefinition, ...] = (
    FeatureDefinition("velocity_1h", "account", "1h", "count", 0, "Transactions in the rolling hour", "feat:acct:{account_id}:velocity_1h", lambda row, hist: _count_window(row, hist, 1)),
    FeatureDefinition("velocity_24h", "account", "24h", "count", 0, "Transactions in the rolling day", "feat:acct:{account_id}:velocity_24h", lambda row, hist: _count_window(row, hist, 24)),
    FeatureDefinition("amount_zscore", "account", "30d", "zscore", 0.0, "Amount versus account baseline", "feat:acct:{account_id}:amount_zscore"),
    FeatureDefinition("device_sharing_degree", "device", "30d", "nunique", 0, "Accounts observed on the device", "feat:device:{device_id}:sharing_degree"),
    FeatureDefinition("graph_risk", "graph", "1h", "propagated_risk", 0.0, "Risk propagated from known-fraud entities", "gfeat:acct:{account_id}:risk"),
    FeatureDefinition("new_device", "account", "all", "first_seen", False, "Whether device is unseen for account", "feat:acct:{account_id}:new_device"),
    FeatureDefinition("off_hours", "transaction", "instant", "hour_bucket", 0, "Transaction at unusual local hour", "feat:txn:off_hours"),
    FeatureDefinition("counterparty_risk", "account", "90d", "max", 0.0, "Counterparty risk aggregate", "feat:acct:{account_id}:counterparty_risk"),
)


def feature_names() -> list[str]:
    return [feature.name for feature in FEATURE_DEFINITIONS]


def defaults() -> dict[str, float | int | bool]:
    return {feature.name: feature.default for feature in FEATURE_DEFINITIONS}
