"""Point-in-time offline feature builder for the M2 feature store.

The loops are intentionally explicit instead of using a convenience rolling window: the
window boundary, tie order, profile-before-update rule, and graph snapshot cutoff are
reviewable and can be mirrored by the Redis script exactly.
"""

from __future__ import annotations

import argparse
import math
import os
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import definitions as D

COLUMNS = ["id", "ts", "account_id", "amount_minor", "device_id", "ip_id"]


def prepare(txns: pd.DataFrame) -> pd.DataFrame:
    frame = txns.copy()
    if "amount_minor" not in frame:
        frame["amount_minor"] = [D.amount_minor(amount) for amount in frame["amount"]]
    for column in ("id", "account_id", "device_id", "ip_id"):
        if column not in frame:
            frame[column] = None
        frame[column] = frame[column].map(
            lambda value: None if value is None or (isinstance(value, float) and math.isnan(value)) else str(value)
        )
    frame["ts"] = pd.to_datetime(frame["ts"], utc=True)
    frame["t"] = [D.epoch_seconds(value.to_pydatetime()) for value in frame["ts"]]
    return frame.sort_values(["t", "id"], kind="mergesort").reset_index(drop=True)


def _windowed_counts(times: np.ndarray, amounts: np.ndarray, window: int) -> tuple[np.ndarray, np.ndarray]:
    count = np.zeros(len(times))
    total = np.zeros(len(times))
    prefix = np.concatenate([[0], np.cumsum(amounts)])
    left = 0
    for index in range(len(times)):
        cutoff = times[index] - window
        while left <= index and times[left] <= cutoff:
            left += 1
        count[index] = index - left + 1
        total[index] = prefix[index + 1] - prefix[left]
    return count, total


def _windowed_distinct(times: np.ndarray, keys: list[str | None], window: int) -> np.ndarray:
    output = np.zeros(len(times))
    live: Counter[str] = Counter()
    left = 0
    for index in range(len(times)):
        cutoff = times[index] - window
        while left <= index and times[left] <= cutoff:
            key = keys[left]
            if key is not None:
                live[key] -= 1
                if live[key] == 0:
                    del live[key]
            left += 1
        if keys[index] is not None:
            live[keys[index]] += 1
        output[index] = len(live)
    return output


def _profile(amounts_minor: np.ndarray, times: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    zscore = np.zeros(len(times))
    seconds_since_prev = np.full(len(times), -1.0)
    mean, m2, last = 0.0, 0.0, None
    for index, (amount, timestamp) in enumerate(zip(amounts_minor, times)):
        n = index
        value = amount / 100
        if n >= 2:
            standard_deviation = math.sqrt(m2 / (n - 1))
            if standard_deviation > 0:
                zscore[index] = (value - mean) / standard_deviation
        if last is not None:
            seconds_since_prev[index] = timestamp - last
        next_n = index + 1
        delta = value - mean
        mean += delta / next_n
        m2 += delta * (value - mean)
        last = timestamp
    return zscore, seconds_since_prev


def build(txns: pd.DataFrame, snapshots: pd.DataFrame | None = None) -> pd.DataFrame:
    frame = prepare(txns)
    output = pd.DataFrame({"id": frame["id"], "ts": frame["ts"], "account_id": frame["account_id"]})
    for name in D.FEATURE_LIST:
        output[name] = float(D.BY_NAME[name].default)

    for _, group in frame.groupby("account_id", sort=False, dropna=False):
        indexes = group.index.to_numpy()
        times = group["t"].to_numpy(dtype=float)
        amounts = group["amount_minor"].to_numpy(dtype=np.int64)
        for label, window in D.WINDOWS.items():
            counts, totals = _windowed_counts(times, amounts, window)
            output.loc[indexes, f"txn_count_{label}"] = counts
            output.loc[indexes, f"amount_sum_minor_{label}"] = totals
        output.loc[indexes, "distinct_devices_24h"] = _windowed_distinct(times, group["device_id"].tolist(), D.DISTINCT_WINDOW_S)
        output.loc[indexes, "distinct_ips_24h"] = _windowed_distinct(times, group["ip_id"].tolist(), D.DISTINCT_WINDOW_S)
        zscore, since = _profile(amounts, times)
        output.loc[indexes, "amount_zscore"] = zscore
        output.loc[indexes, "seconds_since_prev"] = since

    for column, feature in (("device_id", "device_accounts_7d"), ("ip_id", "ip_accounts_7d")):
        for _, group in frame[frame[column].notna()].groupby(column, sort=False, dropna=False):
            output.loc[group.index, feature] = _windowed_distinct(group["t"].to_numpy(dtype=float), group["account_id"].tolist(), D.SHARE_WINDOW_S)

    calendar = pd.DataFrame([D.calendar(value.to_pydatetime()) for value in frame["ts"]], index=frame.index)
    output[["hour_of_day", "day_of_week"]] = calendar[["hour_of_day", "day_of_week"]]
    if snapshots is not None and len(snapshots):
        output = attach_graph(output, snapshots)
    output.attrs["feature_set_version"] = D.FEATURE_SET_VERSION
    return output[["id", "ts", "account_id"] + D.FEATURE_LIST]


def attach_graph(features: pd.DataFrame, snapshots: pd.DataFrame) -> pd.DataFrame:
    snapshot = snapshots.rename(columns={"entity_id": "account_id"}).copy()
    snapshot["account_id"] = snapshot["account_id"].astype(str)
    snapshot["computed_at"] = pd.to_datetime(snapshot["computed_at"], utc=True)
    snapshot = snapshot.sort_values("computed_at")
    left = features.drop(columns=list(D.GRAPH_FIELDS)).reset_index().sort_values("ts")
    merged = pd.merge_asof(left, snapshot, left_on="ts", right_on="computed_at", by="account_id", direction="backward")
    for name, column in D.GRAPH_FIELDS.items():
        merged[name] = merged[column].astype(float).fillna(D.BY_NAME[name].default)
    return merged.sort_values("index").set_index("index").rename_axis(None)[features.columns]


def compute_features(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Small list-in/list-out compatibility wrapper used by the M1 demo and notebooks."""
    frame = build(pd.DataFrame(rows))
    records = frame.to_dict(orient="records")
    for record in records:
        for alias, canonical in D.LEGACY_ALIASES.items():
            value = record[canonical]
            # M1's compatibility contract exposed history before the current row;
            # the canonical M2 contract intentionally includes the current row.
            record[alias] = max(value - 1.0, 0.0) if alias.startswith("velocity_") else value
        source = next((row for row in rows if str(row.get("id")) == record["id"]), {})
        if "label" in source:
            record["label"] = source["label"]
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    import sqlalchemy as sa

    engine = sa.create_engine(os.environ["DATABASE_URL"])
    transactions = pd.read_sql("SELECT id, ts, account_id, amount, device_id, ip_id FROM transactions", engine)
    try:
        snapshots = pd.read_sql("SELECT entity_id, computed_at, component_size, dist_to_fraud, risk_rank FROM graph_feature_snapshots", engine)
    except Exception:  # noqa: BLE001 - M1 databases may not have the M2 table before migration.
        snapshots = pd.DataFrame()
    output = build(transactions, snapshots)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    output.to_parquet(args.out, index=False)
    print(f"{len(output)} rows x {len(D.FEATURE_LIST)} features (feature set {D.FEATURE_SET_VERSION}) -> {args.out}")


if __name__ == "__main__":
    main()
