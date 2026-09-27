# AegisFlow architecture

## Runtime topology

```text
payment gateway / txgen
        │ POST /api/v1/transactions
        ▼
 FastAPI ingestion boundary ───────► Postgres (transactions, decisions, cases, audit)
        │                                   ▲
        ├── online feature adapter ─► Redis  │
        │   (Lua velocity + profiles)       │
        ▼                                   │
 low-latency scorer                       │
 rules → champion → challenger shadow       │
 SHAP-shaped reason codes                   │
        │                                   │
        ├── approve / decision feed         │
        └── review / decline → alerts ──────┘
                                             │
                                             ▼
              supervisor → link · pattern · media · writer · QA
                                             │
                                      evidence pack + SAR draft
                                             │
                              human edit → manager approval → export
```

The repository has a unified `services/platform` API for a zero-setup demo and separate packages under `services/ingestion`, `services/scoring`, `services/casework`, and `services/investigator` for deployment boundaries. The platform API does not call a model or database from the latency-critical scoring function: it reads the online feature contract, scores, then persists the result. A production split can move the scorer behind a service key without changing the contract.

## Latency budget

| Segment | Target | Demo implementation |
| --- | ---: | --- |
| schema validation | 2 ms | Pydantic request model |
| feature read | 5 ms | one in-memory read; Redis adapter uses one pipeline |
| rules + model | 20 ms | pure Python calibrated-compatible runtime |
| explanation | 5 ms | precomputed reason contribution mapping |
| API overhead | 20 ms | FastAPI threadpool + connection pool |
| budget | **<100 ms p95** | measured by `/metrics`; `latency_ms` is returned per decision |

## Data contracts and integrity

- `ml/src/aegis_ml/features/definitions.py` is the single feature declaration module. Offline computation and the online `OnlineFeatureReader` use the same names, windows, aggregations, and defaults.
- Transaction labels are emitted to `data/ground_truth.jsonl` only. Serving rows never read this sink.
- Decisions and business changes write an audit row in the same SQLAlchemy session. A production Postgres deployment should relay the same row through an outbox consumer to a WORM destination.
- SAR drafts are immutable versions. Editing creates v2, v3, and so on; the API rejects export unless the latest version is `approved`.
- The investigation writer receives typed findings/evidence IDs, not raw SQL or untrusted retrieved text. QA checks citation IDs and approval is a manager-only operation.

## Availability and degraded mode

If Redis is unavailable, the scorer may use account defaults and returns `degraded=true` plus `feature_store_hit=false`. Conservative deterministic rules still run. The demo's in-memory reader makes this path testable without Redis. Health endpoints are `/health` and `/ready`; Compose has restart policies and database health checks.

## Deployment mapping

Compose provisions PostgreSQL, Redis, Qdrant, API, and frontend. For a cloud deployment map them to RDS, ElastiCache, Qdrant Cloud/OpenSearch vector storage, ECS/Fargate, and a TLS reverse proxy. No cloud account is needed for the synthetic demo. MLflow and Kafka are intentionally future infrastructure seams; the model registry and event contracts are already represented by the API and `registry.py` extension points.
