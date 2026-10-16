# AegisFlow

> Real-time payment risk scoring and human-controlled AML investigations.

AegisFlow is a runnable reference implementation of the platform described in the project brief. It pairs a millisecond-friendly hybrid fraud decision engine with a case workbench that assembles an evidence pack, drafts a citation-linked SAR narrative, and requires a human approval before export.

## What is implemented

- **Live scoring path** — one pipelined feature read, behavioral and velocity features, graph-risk signals, deterministic rule hits, calibrated-looking probability, top-five reason codes, degraded mode, and champion/challenger shadow metrics.
- **Synthetic traffic** — reproducible accounts, devices, merchants, fraud rings, smurfing, layering, and round-tripping labels. Ground truth is kept separate from serving data.
- **Case operations** — alert correlation, SLA/priority scoring, evidence packs, typology findings, graph data, media excerpts, versioned SAR drafts, disposition, approval rationale, and immutable audit events.
- **Investigation workflow** — typed deterministic specialist agents (link, pattern, adverse media, narrative writer, QA reviewer) with explicit evidence IDs. The seams are ready for LangGraph/Qdrant in a production deployment without making the local demo dependent on an LLM.
- **Analyst console** — live decision feed, case queue, case workspace, graph/timeline/evidence panels, SAR editor, approval gate, model health, drift, and threshold controls.
- **Operational foundation** — FastAPI/OpenAPI, SQLAlchemy schema, Redis-ready online feature store, Postgres/Redis/Qdrant compose services, Prometheus metrics, health checks, CI, and feature parity tests.

## Quick start: browser demo

The frontend includes a graceful demo fallback, so it can be explored without infrastructure. To run the API-backed experience:

```bash
cp .env.example .env
python -m venv .venv && source .venv/bin/activate
pip install -r services/platform/requirements.txt
make dev-api                 # http://localhost:8000
# in a second shell:
cd frontend && npm install && npm run dev -- --host 0.0.0.0
```

Open the Vite URL. API docs are at `http://localhost:8000/docs`.

Or run the infrastructure-backed stack:

```bash
cp .env.example .env
make up                       # Postgres, Redis, Qdrant, API, frontend
make seed
make generate COUNT=100
```

The default compose profile serves the console at `http://localhost:5173`. The local API deliberately uses the same relative `/api` paths as production; the browser never calls `localhost` for a second service.

## Useful commands

```bash
make test                     # Python unit/API tests
make lint                     # ruff + frontend type check when installed
make generate COUNT=250       # stream synthetic events into the ingestion API
make train                    # build a small reproducible baseline artifact
make loadtest                 # optional Locust profile

# M2 feature-store / entity-graph checks (fakeredis works without Docker)
make test-m2
make verify-m2
# With Postgres + Redis running:
make migrate && make seed-fraud && make up-m2
```

M2's authenticated ingestion service listens on port `8001` and accepts `X-Service-Key` on `POST /api/v1/transactions`. It commits the transaction and typed entity edges before the atomic Redis Lua update; the response keeps `decision: null` until M4. `make parity` can additionally replay the exact 5,000-row proof against `PARITY_REDIS_URL` (use a scratch Redis database).

Demo credentials are intentionally non-sensitive and only enabled when `DEMO_MODE=true`:

| Role | Email | Password |
| --- | --- | --- |
| AML analyst | `priya@aegisflow.demo` | `demo` |
| Manager / MLRO | `marcus@aegisflow.demo` | `demo` |
| Fraud analyst | `fraud@aegisflow.demo` | `demo` |

## Repository map

- `services/scoring` — feature reader, rule registry, decision policy, explanations, shadow metrics.
- `services/platform` — API composition, persistence, seeded demo, case/SAR endpoints.
- `services/ingestion` — transaction schemas and the ingestion boundary.
- `services/casework` — correlation, priority, audit, and FinCEN-style export helpers.
- `services/investigator` — typed investigation state, deterministic tools/agents, QA gate.
- `ml` — single-source feature definitions, offline builder, graph job, evaluation and drift utilities.
- `generator` — population and labeled typology stream generator.
- `frontend` — React + Vite analyst console.
- `docs` — architecture, typologies, ADRs, runbook, and security notes.

## Safety and scope

This repository is a synthetic-data demonstration. It does not connect to sanctions providers, submit real SARs, or make autonomous filing decisions. Every draft remains in `draft`/`edited` status until an appropriately authorized human supplies a rationale and approves it. Production deployments must replace demo auth, secrets, data retention, model artifacts, and reference data through the documented controls.
