from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from statistics import mean, pstdev
from typing import Any

from .definitions import FEATURE_DEFINITIONS, defaults


def compute_features(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Point-in-time feature builder using only rows earlier than the scored event."""
    ordered = sorted(rows, key=lambda row: row["ts"])
    history: list[dict[str, Any]] = []
    device_accounts: dict[str, set[str]] = defaultdict(set)
    output: list[dict[str, Any]] = []
    for row in ordered:
        values = defaults()
        own = [item for item in history if item.get("account_id") == row.get("account_id")]
        amounts = [float(item.get("amount", 0)) for item in own[-100:]]
        avg = mean(amounts) if amounts else float(row.get("amount", 0))
        std = pstdev(amounts) if len(amounts) > 1 else max(avg * 0.5, 1)
        for definition in FEATURE_DEFINITIONS:
            if definition.extractor:
                values[definition.name] = definition.extractor(row, history)
        values["amount_zscore"] = (float(row.get("amount", 0)) - avg) / max(std, 1)
        values["device_sharing_degree"] = len(device_accounts[row.get("device_id", "")])
        values["new_device"] = bool(row.get("device_id")) and row.get("device_id") not in {x.get("device_id") for x in own}
        ts = row["ts"]
        values["off_hours"] = int(ts.hour < 5 or ts.hour >= 23)
        output.append({"id": row.get("id"), "account_id": row.get("account_id"), "ts": ts, "label": row.get("label", 0), **values})
        history.append(row)
        if row.get("device_id"):
            device_accounts[row["device_id"]].add(row.get("account_id", ""))
    return output
