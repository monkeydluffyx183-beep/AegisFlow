from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class AlertRef:
    alert_id: str
    account_id: str
    device_id: str | None = None
    ip_id: str | None = None
    ring_id: str | None = None


def correlate(alerts: Iterable[AlertRef]) -> list[list[str]]:
    """Connected-component clustering across account/device/IP/ring keys."""
    rows = list(alerts)
    parent = list(range(len(rows)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    buckets: dict[str, int] = {}
    for idx, row in enumerate(rows):
        keys = [f"acct:{row.account_id}"]
        keys += [f"device:{row.device_id}"] if row.device_id else []
        keys += [f"ip:{row.ip_id}"] if row.ip_id else []
        keys += [f"ring:{row.ring_id}"] if row.ring_id else []
        for key in keys:
            if key in buckets:
                union(idx, buckets[key])
            else:
                buckets[key] = idx
    components: dict[int, list[str]] = defaultdict(list)
    for idx, row in enumerate(rows):
        components[find(idx)].append(row.alert_id)
    return list(components.values())
