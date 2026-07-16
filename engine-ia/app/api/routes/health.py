"""Endpoints de saude/observabilidade."""
from __future__ import annotations

from fastapi import APIRouter

from app.cache.redis_client import get_redis
from app.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}


@router.get("/ready")
def ready() -> dict:
    redis_ok = get_redis() is not None
    return {
        "status": "ready",
        "llm_mode": "stub" if settings.llm_use_stub else "azure",
        "redis": "up" if redis_ok else "down",
    }
