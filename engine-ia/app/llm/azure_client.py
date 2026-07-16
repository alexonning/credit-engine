"""Camada LLM. Seleciona o provedor e oferece um stub deterministico.

Provedores suportados (via LLM_PROVIDER): Azure OpenAI e Anthropic (Claude). O
stub (LLM_USE_STUB=true) permite rodar todo o pipeline sem credenciais e sem
custo, com saida reproduzivel - essencial para testes e desenvolvimento local.
Os AGENTES nunca decidem via LLM: o LLM apenas gera texto de racional/explicacao
sobre findings ja calculados pelo Rule Engine (LLM desacoplado da decisao).
"""
from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache
from typing import Protocol

from app.config import settings
from app.core.logging import get_logger

logger = get_logger("llm")


class LLMClient(Protocol):
    def complete(self, system: str, user: str) -> str: ...

    def stream(self, system: str, user: str) -> Iterator[str]: ...


class StubLLM:
    """Gera texto deterministico a partir do prompt (sem chamar API externa)."""

    def complete(self, system: str, user: str) -> str:
        # Retorna um resumo simples e estavel para desenvolvimento/testes.
        first_line = user.strip().splitlines()[0] if user.strip() else ""
        return f"[stub-llm] {first_line[:180]}"

    def stream(self, system: str, user: str) -> Iterator[str]:
        # Simula o streaming quebrando o texto do stub em pedacos (tokens).
        text = self.complete(system, user)
        for token in text.split(" "):
            yield token + " "


class AzureLLM:
    """Wrapper fino sobre a API do Azure OpenAI (chat completions)."""

    def __init__(self) -> None:
        from openai import AzureOpenAI

        self._client = AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )
        self._deployment = settings.azure_openai_deployment

    def complete(self, system: str, user: str) -> str:
        resp = self._client.chat.completions.create(
            model=self._deployment,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
            max_tokens=500,
        )
        return resp.choices[0].message.content or ""

    def stream(self, system: str, user: str) -> Iterator[str]:
        stream = self._client.chat.completions.create(
            model=self._deployment,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
            max_tokens=500,
            stream=True,
        )
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta


@lru_cache
def get_llm() -> LLMClient:
    if settings.llm_use_stub:
        logger.info("llm_mode", mode="stub")
        return StubLLM()

    provider = settings.llm_provider.lower()
    if provider == "anthropic":
        # import tardio: so exige o SDK anthropic quando este provedor e usado
        from app.llm.anthropic_client import AnthropicLLM

        logger.info("llm_mode", mode="anthropic", model=settings.anthropic_model)
        return AnthropicLLM()

    logger.info("llm_mode", mode="azure", deployment=settings.azure_openai_deployment)
    return AzureLLM()
