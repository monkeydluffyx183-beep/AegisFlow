"""Ingestion settings from environment variables (development defaults only)."""

from __future__ import annotations

import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://aegis:aegis_dev_2026@localhost:5432/aegisflow")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
SERVICE_KEY = os.getenv("SERVICE_KEY", os.getenv("SERVICE_API_KEY", "dev-service-key"))
