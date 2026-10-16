.PHONY: help up m2-up up-m2 down m2-down dev-api dev-ingestion ingest dev-frontend seed seed-fraud generate train test parity graph-once features-pit migrate test-m2 test-m2-int m2 lint loadtest verify verify-m2 clean

PYTHON ?= python3
PYTHONPATH := services/platform/src:services/scoring/src:services/ingestion/src:services/casework/src:services/investigator/src:ml/src:generator/src
M2_PATH := PYTHONPATH=services/ingestion/src:ml/src:.
M2_COMPOSE := docker compose -f docker-compose.yml -f docker-compose.m2.yml

help:
	@echo "AegisFlow targets: up m2-up up-m2 down m2-down dev-api ingest dev-frontend seed seed-fraud generate train test parity graph-once features-pit migrate test-m2 test-m2-int m2 lint loadtest verify verify-m2"

up:
	docker compose up -d --build

m2-up:
	$(M2_COMPOSE) up -d --build

up-m2:
	$(M2_COMPOSE) up -d --build ingestion graph-job

down:
	docker compose down

m2-down:
	docker compose -f docker-compose.yml -f docker-compose.m2.yml down

dev-api:
	mkdir -p data
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m uvicorn aegisflow_platform.main:app --reload --host 0.0.0.0 --port $${API_PORT:-8000}

dev-ingestion:
	$(M2_PATH) uvicorn ingestion.main:app --reload --host 0.0.0.0 --port $${INGESTION_PORT:-8001}

ingest:
	$(M2_PATH) uvicorn ingestion.main:app --reload --host 0.0.0.0 --port $${INGESTION_PORT:-8001}

dev-frontend:
	cd frontend && npm run dev -- --host 0.0.0.0

seed:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m aegisflow_platform.seed

seed-fraud:
	$(M2_PATH) $(PYTHON) db/seed/seed_known_fraud.py

generate:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m txgen.main --count $${COUNT:-100} --endpoint $${INGEST_URL:-http://localhost:8000/api/v1/transactions}

train:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m aegis_ml.training.train_fraud --output data/models/baseline.json

test:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pytest -q

parity:
	$(M2_PATH) PARITY_REDIS_URL=$${PARITY_REDIS_URL:-redis://localhost:6379/15} $(PYTHON) -m pytest -q tests/m2/unit/test_m2_parity.py

graph-once:
	$(M2_PATH) $(PYTHON) -m aegis_ml.features.graph_features --once

features-pit:
	dvc repro features_pit

test-m2:
	$(M2_PATH) $(PYTHON) -m pytest -q tests/m2/unit tests/m2/api

test-m2-int:
	$(M2_PATH) $(PYTHON) -m pytest -q tests/m2/integration

m2:
	$(MAKE) test-m2
	$(MAKE) test-m2-int
	$(MAKE) verify-m2

migrate:
	DATABASE_URL=$${DATABASE_URL:-postgresql+psycopg://aegis:aegis_dev_2026@localhost:5432/aegisflow} $(PYTHON) -m alembic -c alembic.ini upgrade head

lint:
	PYTHONPATH=$(PYTHONPATH) ruff check services generator ml tests db scripts
	cd frontend && npm run typecheck

loadtest:
	locust -f tests/load/locustfile.py --host http://localhost:8000 --headless -u 30 -r 10 -t 30s

verify:
	@echo "Checking repository contract..."
	@test -f services/scoring/src/scoring/engine.py
	@test -f ml/src/aegis_ml/features/definitions.py
	@test -f services/investigator/src/investigator/orchestrator/graph.py
	@test -f frontend/src/App.tsx
	@echo "AegisFlow M1/MVP checks passed"

verify-m2:
	$(M2_PATH) $(PYTHON) scripts/verify_m2.py

clean:
	rm -rf data/*.db data/models .pytest_cache
