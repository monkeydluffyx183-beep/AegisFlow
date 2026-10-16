-- Reference PostgreSQL schema for deployments using Alembic/SQL migrations.
-- The demo API creates equivalent SQLAlchemy tables automatically.
CREATE TABLE IF NOT EXISTS audit_log (
  id VARCHAR(64) PRIMARY KEY,
  actor_id VARCHAR(96) NOT NULL,
  actor_role VARCHAR(32) NOT NULL,
  action VARCHAR(96) NOT NULL,
  resource_type VARCHAR(32) NOT NULL,
  resource_id VARCHAR(96) NOT NULL,
  detail JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_audit_resource ON audit_log(resource_id, created_at DESC);

CREATE TABLE IF NOT EXISTS threshold_config (
  id INTEGER PRIMARY KEY,
  review_threshold REAL NOT NULL CHECK (review_threshold > 0 AND review_threshold < 1),
  decline_threshold REAL NOT NULL CHECK (decline_threshold > review_threshold AND decline_threshold < 1),
  version INTEGER NOT NULL DEFAULT 1,
  updated_by VARCHAR(96) NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Entity, transaction, decision, alert, case, evidence, and SAR tables are represented by
-- SQLAlchemy models in services/platform/src/aegisflow_platform/db.py. This seed migration
-- intentionally only anchors immutable audit/policy invariants for an external migration runner.
