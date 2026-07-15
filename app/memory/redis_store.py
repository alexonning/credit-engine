"""Armazenamento de estado de workflow e cache em Redis."""
import json
from typing import Any

import redis.asyncio as aioredis

from app.config.settings import get_settings


class RedisStore:
    def __init__(self, url: str | None = None) -> None:
        self._client = aioredis.from_url(
            url or str(get_settings().redis_url),
            decode_responses=True,
        )

    async def salvar_estado(self, analysis_id: str, estado: dict[str, Any], ttl_s: int = 86400) -> None:
        await self._client.set(
            f"analise:{analysis_id}:estado",
            json.dumps(estado, ensure_ascii=False, default=str),
            ex=ttl_s,
        )

    async def carregar_estado(self, analysis_id: str) -> dict[str, Any] | None:
        raw = await self._client.get(f"analise:{analysis_id}:estado")
        return json.loads(raw) if raw else None

    async def cache_set(self, chave: str, valor: str, ttl_s: int = 3600) -> None:
        await self._client.set(f"cache:{chave}", valor, ex=ttl_s)

    async def cache_get(self, chave: str) -> str | None:
        return await self._client.get(f"cache:{chave}")

    async def fechar(self) -> None:
        await self._client.aclose()
