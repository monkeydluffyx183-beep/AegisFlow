# AegisFlow local runbook

## Start / stop

```bash
cp .env.example .env
make up
# API: http://localhost:8000/health, docs: http://localhost:8000/docs
# Console: http://localhost:5173
make down
```

The API creates its schema and seeds synthetic demo data on first boot. If Postgres is unavailable, use `make dev-api` after installing `services/platform/requirements.txt`; the default SQLite database is `data/aegisflow.db`.

## Demo flow

1. Open the console and choose **Live decisions**. Inspect a decline's score, reason codes, rule hits, and latency.
2. Open **Case queue**, select the critical coordinated smurfing case, and inspect the graph, timeline, typology match, media excerpt, and draft citations.
3. Select **Run investigation** on a case without evidence to rerun the typed specialist workflow.
4. Edit the SAR textarea and save a new immutable version.
5. Use the approval rationale and **Approve & prepare export**. The API sends manager headers in demo mode and records `sar.approved`; no filing is sent to a regulator.
6. Review **Model ops** to tune thresholds, inspect champion/challenger status, and watch PSI.

## M2 feature store and ingestion

After Postgres and Redis are healthy, run the M2 migration and pre-T0 seed:

```bash
make migrate
make seed-fraud
make up-m2
curl -H "X-Service-Key: ${SERVICE_KEY:-local-demo-service-key}" http://localhost:8001/ready
```

The M2 endpoint is `POST http://localhost:8001/api/v1/transactions`. It is event-time based, uses integer minor units inside Redis, and returns `{id, decision: null, duplicate}`. A successful database commit followed by a Redis outage returns `503`; retry the same UUID so the Lua idempotency key completes the feature update without duplicating edges. Run `make graph-once` hourly in a scheduler (the Compose graph job defaults to one hour).

For the release proof, `make verify-m2` runs fakeredis exact parity over 5,000 deterministic transactions. Set `PARITY_REDIS_URL` to a scratch Redis database to run the same proof against real Redis; never point it at live feature keys.

## Synthetic streaming

```bash
PYTHONPATH=generator/src python -m txgen.main --count 250 --endpoint http://localhost:8000/api/v1/transactions --replay 0.02
```

`data/ground_truth.jsonl` is the evaluation-only label sink. Never mount it into the scoring service in production.

## Operational checks

```bash
curl localhost:8000/health
curl localhost:8000/ready
curl localhost:8000/metrics
curl localhost:8000/openapi.json > /tmp/aegisflow-openapi.json
```

A latency regression means inspecting Redis hit rate, database connection pool wait, and model loading. The score response explicitly reports `degraded` so a Redis failure is visible to downstream analysts.

## Recovery / rollback

- Threshold rollback: restore the previous policy in the ModelOps UI or `PUT /api/v1/thresholds` as a manager; the change is versioned and audited.
- Model rollback: promote the previous champion in the registry process; do not hot-edit model files in the running container.
- Case recovery: investigation is idempotent. Rerun replaces agent-generated evidence for the case and creates a fresh audit event.
- Database recovery: restore Postgres from the managed snapshot, then re-run health/readiness. Never rewrite `audit_log` or SAR versions.

## Security checklist before production

Replace demo auth and secret defaults, use TLS and service-key rotation, encrypt PII columns, mask entity labels by role, disable raw request logging, enable Postgres row/team policies, connect Redis/Qdrant with auth/TLS, and require an independent manager/MLRO approval service. Retrieved media remains untrusted and tool calls stay allowlisted.
