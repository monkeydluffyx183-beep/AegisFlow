"""Process singletons. Tests replace these module globals with MemoryStore/fakeredis."""

from __future__ import annotations

from typing import Any

import redis
from sqlalchemy import create_engine

from . import config
from .persistence import PgStore

_store: Any = None
_redis: Any = None


def store() -> Any:
    global _store
    if _store is None:
        _store = PgStore(create_engine(config.DATABASE_URL, pool_pre_ping=True))
    return _store


def redis_client() -> Any:
    global _redis
    if _redis is None:
        _redis = redis.Redis.from_url(config.REDIS_URL)
    return _redis
