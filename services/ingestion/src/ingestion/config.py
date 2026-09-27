import os
from dataclasses import dataclass


@dataclass(frozen=True)
class IngestionConfig:
    service_api_key: str = os.getenv("SERVICE_API_KEY", "local-demo-service-key")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    max_body_bytes: int = 128_000
