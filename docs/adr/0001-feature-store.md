# ADR 0001 — Feature-store parity rules (M2)

- Status: accepted
- Scope: Milestone 2 feature store and entity graph

## Decision

`ml/src/aegis_ml/features/definitions.py` is the only declaration point for the 19 online/offline features. The offline builder and the Redis Lua script import its windows, defaults, output ordering, and feature-set version. The parity suite must compare every row and every column with exact equality.

The implementation commits to these rules:

- **D1 — event time:** windows use the transaction `ts` passed to Lua, never Redis `TIME`.
- **D2 — boundaries:** windows are `(ts - w, ts]`, include the current transaction, and order ties by `(ts, id)`.
- **D3 — idempotency:** `SET seen:txn:{id} NX` is inside the atomic script; money crosses Redis as integer minor units.
- **D4 — profile order:** amount z-score reads Welford's profile before the current amount is added; online and offline use the same order.
- **D5 — known fraud:** serving graph features use only `known_fraud_entities` confirmed before cutoff `T0`, never the raw ground-truth label table.
- **D6 — edge uniqueness:** `(src_type, src_id, dst_type, dst_id, edge_type)` is unique; retries do not inflate edge weights.
- **D7 — snapshots:** the graph job writes hourly snapshots; offline features join the latest snapshot with `computed_at <= transaction.ts`.
- **D8 — entity upserts:** generic entity upsert endpoints remain deferred; the synthetic generator owns entity seeding.

Floats returned from Lua are strings formatted with `%.17g` before client conversion, avoiding integer truncation and preserving exact parity. Redis graph hashes have a two-hour TTL so one missed hourly run is visible but not immediately destructive.
