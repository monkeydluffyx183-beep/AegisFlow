.PHONY: help up down dev-api dev-frontend seed generate train test lint loadtest verify clean

PYTHON ?= python3
PYTHONPATH := services/platform/src:services/scoring/src:services/ingestion/src:services/casework/src:services/investigator/src:ml/src:generator/src

help:
	@echo "AegisFlow targets: up down dev-api dev-frontend seed generate train test lint loadtest verify"

up:
	docker compose up -d --build

down:
	docker compose down

dev-api:
	mkdir -p data
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m uvicorn aegisflow_platform.main:app --reload --host 0.0.0.0 --port $${API_PORT:-8000}

dev-frontend:
	cd frontend && npm run dev -- --host 0.0.0.0

seed:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m aegisflow_platform.seed

generate:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m txgen.main --count $${COUNT:-100} --endpoint $${INGEST_URL:-http://localhost:8000/api/v1/transactions}

train:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m aegis_ml.training.train_fraud --output data/models/baseline.json

test:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pytest -q

lint:
	PYTHONPATH=$(PYTHONPATH) ruff check services generator ml tests
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

clean:
	rm -rf data/*.db data/models .pytest_cache
