"""Idempotent transaction and entity-edge persistence for the M2 ingestion boundary."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from .schemas import TransactionIn

INSERT_TXN = text(
    """
    INSERT INTO transactions (id, ts, account_id, counterparty_id, merchant_id, device_id, ip_id,
                              amount, currency, channel, country, status, raw)
    VALUES (:id, :ts, :account_id, :counterparty_id, :merchant_id, :device_id, :ip_id,
            :amount, :currency, :channel, :country, :status, :raw)
    ON CONFLICT (id) DO NOTHING
    RETURNING id
    """
)
ENTITY_EXISTS = text("SELECT 1 FROM entities WHERE id = :entity_id AND entity_type = :entity_type LIMIT 1")

UPSERT_EDGE = text(
    """
    INSERT INTO entity_edges (src_type, src_id, dst_type, dst_id, edge_type, first_seen, weight)
    VALUES (:src_type, :src_id, :dst_type, :dst_id, :edge_type, :ts, 1)
    ON CONFLICT (src_type, src_id, dst_type, dst_id, edge_type)
    DO UPDATE SET weight = entity_edges.weight + 1
    """
)


class UnknownEntity(ValueError):
    """A referenced entity does not exist or violates a foreign key."""


def edges_for(transaction: TransactionIn) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    for kind, value, edge_type in (
        ("device", transaction.device_id, "uses_device"),
        ("ip", transaction.ip_id, "uses_ip"),
        ("merchant", transaction.merchant_id, "pays_merchant"),
    ):
        if value:
            edges.append({"src_type": "account", "src_id": str(transaction.account_id), "dst_type": kind, "dst_id": str(value), "edge_type": edge_type, "ts": transaction.ts})
    if transaction.channel == "transfer" and transaction.counterparty_id:
        edges.append({"src_type": "account", "src_id": str(transaction.account_id), "dst_type": "account", "dst_id": str(transaction.counterparty_id), "edge_type": "transfers_to", "ts": transaction.ts})
    return edges


class PgStore:
    def __init__(self, engine: Any):
        self.engine = engine

    def store(self, transaction: TransactionIn) -> bool:
        """Return true only when the transaction and its edges were inserted now."""
        try:
            with self.engine.begin() as connection:
                referenced = [("account", transaction.account_id), ("account", transaction.counterparty_id), ("merchant", transaction.merchant_id), ("device", transaction.device_id), ("ip", transaction.ip_id)]
                for entity_type, entity_id in referenced:
                    if entity_id and connection.execute(ENTITY_EXISTS, {"entity_id": str(entity_id), "entity_type": entity_type}).first() is None:
                        raise UnknownEntity(f"{entity_type}:{entity_id}")
                params = {
                    "id": str(transaction.id),
                    "ts": transaction.ts,
                    "account_id": str(transaction.account_id),
                    "counterparty_id": str(transaction.counterparty_id) if transaction.counterparty_id else None,
                    "merchant_id": str(transaction.merchant_id) if transaction.merchant_id else None,
                    "device_id": str(transaction.device_id) if transaction.device_id else None,
                    "ip_id": str(transaction.ip_id) if transaction.ip_id else None,
                    "amount": float(transaction.amount),
                    "currency": transaction.currency,
                    "channel": transaction.channel,
                    "country": "US",
                    "status": "received",
                    "raw": "{}",
                }
                inserted = connection.execute(INSERT_TXN, params).first() is not None
                if inserted:
                    for edge in edges_for(transaction):
                        connection.execute(UPSERT_EDGE, edge)
                return inserted
        except IntegrityError as exc:
            if getattr(exc.orig, "sqlstate", None) == "23503":
                raise UnknownEntity(str(exc.orig).splitlines()[0]) from None
            raise

    def ping(self) -> bool:
        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True


class MemoryStore:
    """Small test double with the same created/duplicate semantics as PgStore."""

    def __init__(self, known_accounts: set[str] | None = None):
        self.rows: dict[str, TransactionIn] = {}
        self.edges: dict[tuple[str, str, str, str, str], int] = {}
        self.known = known_accounts

    def store(self, transaction: TransactionIn) -> bool:
        if self.known is not None and str(transaction.account_id) not in self.known:
            raise UnknownEntity("account not found")
        if str(transaction.id) in self.rows:
            return False
        self.rows[str(transaction.id)] = transaction
        for edge in edges_for(transaction):
            key = (edge["src_type"], str(edge["src_id"]), edge["dst_type"], str(edge["dst_id"]), edge["edge_type"])
            self.edges[key] = self.edges.get(key, 0) + 1
        return True

    def ping(self) -> bool:
        return True


def transaction_record(transaction: TransactionIn) -> dict[str, Any]:
    return transaction.model_dump(mode="json")
