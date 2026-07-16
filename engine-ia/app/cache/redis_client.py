"""Cliente Redis para cache de decisoes (idempotencia / performance)."""
from __future__ import annotations

from functools import lru_cache

import redis

from app.config import settings
from app.core.logging import get_logger

logger = get_logger("cache")


@lru_cache
def get_redis() -> redis.Redis | None:
    try:
        client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        client.ping()
        logger.info("redis_connected")
        return client
    except Exception as exc:  # noqa: BLE001 - cache e opcional, degrada com elegancia
        logger.warning("redis_unavailable", error=str(exc))
        return None


def cache_get(key: str) -> str | None:
    client = get_redis()
    if client is None:
        return None
    try:
        return client.get(key)
    except Exception:  # noqa: BLE001
        return None


def cache_set(key: str, value: str, ttl_seconds: int = 3600) -> None:
    client = get_redis()
    if client is None:
        return
    try:
        client.set(key, value, ex=ttl_seconds)
    except Exception:  # noqa: BLE001
        pass
