from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    demo_mode: bool = os.getenv("DEMO_MODE", "true").lower() == "true"
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data/aegisflow.db")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    qdrant_url: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    cors_origins: tuple[str, ...] = tuple(x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if x.strip())
    service_api_key: str = os.getenv("SERVICE_API_KEY", "local-demo-service-key")
    jwt_secret: str = os.getenv("JWT_SECRET", "local-only-change-me")
    review_threshold: float = float(os.getenv("REVIEW_THRESHOLD", "0.45"))
    decline_threshold: float = float(os.getenv("DECLINE_THRESHOLD", "0.76"))


settings = Settings()
