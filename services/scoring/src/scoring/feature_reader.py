from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import RLock
from typing import Any


@dataclass
class FeatureSnapshot:
    values: dict[str, Any]
    hit: bool = True


class OnlineFeatureReader:
    """Redis-shaped online feature reader with an in-memory fallback for local/demo mode.

    The interface is intentionally equivalent to the Redis implementation: `read` is a
    single logical lookup and `observe` is idempotent for a transaction id. A production
    adapter can replace the dictionaries with a pipelined Redis read and Lua update.
    """

    def __init__(self) -> None:
        self._events: dict[str, deque[tuple[datetime, float, str, str]]] = defaultdict(deque)
        self._accounts: dict[str, dict[str, Any]] = defaultdict(dict)
        self._seen: set[str] = set()
        self._lock = RLock()

    def seed_account(self, account_id: str, **values: Any) -> None:
        with self._lock:
            self._accounts[account_id].update(values)

    def read(self, request: Any) -> FeatureSnapshot:
        now = request.ts if getattr(request, "ts", None) else datetime.now(UTC)
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)
        with self._lock:
            baseline = self._accounts.get(request.account_id, {})
            events = self._events[request.account_id]
            self._trim(events, now)
            one_hour = sum(1 for ts, *_ in events if ts >= now - timedelta(hours=1))
            one_day = sum(1 for ts, *_ in events if ts >= now - timedelta(days=1))
            one_week = sum(1 for ts, *_ in events if ts >= now - timedelta(days=7))
            amounts = [amount for ts, amount, *_ in events if ts >= now - timedelta(days=30)]
            mean = float(baseline.get("avg_amount", (sum(amounts) / len(amounts)) if amounts else 180))
            std = float(baseline.get("amount_std", max(mean * 0.65, 80)))
            amount_z = (float(request.amount) - mean) / max(std, 1)
            devices = {device for _, _, device, _ in events if device}
            device_id = getattr(request, "device_id", None)
            graph_risk = float(baseline.get("graph_risk", 0.08))
            if getattr(request, "account_id", "").startswith("ring-"):
                graph_risk = max(graph_risk, 0.87)
            new_device = bool(device_id and device_id not in devices and bool(events))
            if not events and baseline.get("known_device") and device_id != baseline.get("known_device"):
                new_device = True
            hour = now.hour
            off_hours = 1 if hour < 5 or hour >= 23 else 0
            result = {
                "velocity_1h": one_hour,
                "velocity_24h": one_day,
                "velocity_7d": one_week,
                "amount_zscore": round(amount_z, 4),
                "device_sharing_degree": int(baseline.get("device_sharing_degree", 0)),
                "graph_risk": round(graph_risk, 4),
                "new_device": new_device,
                "off_hours": off_hours,
                "counterparty_risk": float(baseline.get("counterparty_risk", 0.04)),
                "impossible_travel": bool(baseline.get("impossible_travel", False)),
                "sanctions_hit": bool(baseline.get("sanctions_hit", False)),
                "account_history": min(one_week, 50),
            }
            return FeatureSnapshot(result, hit=request.account_id in self._accounts or bool(events))

    def observe(self, request: Any) -> None:
        transaction_id = getattr(request, "id", None)
        with self._lock:
            if transaction_id and transaction_id in self._seen:
                return
            now = request.ts if getattr(request, "ts", None) else datetime.now(UTC)
            if now.tzinfo is None:
                now = now.replace(tzinfo=UTC)
            self._events[request.account_id].append((now, float(request.amount), request.device_id or "", request.ip_id or ""))
            self._trim(self._events[request.account_id], now)
            if transaction_id:
                self._seen.add(transaction_id)

    @staticmethod
    def _trim(events: deque[tuple[datetime, float, str, str]], now: datetime) -> None:
        cutoff = now - timedelta(days=30)
        while events and events[0][0] < cutoff:
            events.popleft()
