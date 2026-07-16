"""Contrato comum de fábrica de LLM e seletor de provedor.

Permite alternar entre Azure OpenAI e Anthropic (Claude) sem alterar os agentes:
ambas as fábricas satisfazem estruturalmente o Protocol `LLMFactory`.
"""
from typing import Protocol

from langchain_core.language_models import BaseChatModel

from app.config.settings import Settings, get_settings
from app.services.llm.azure_client import AzureLLMFactory, ModelTier


class LLMFactory(Protocol):
    """Interface mínima exigida pelos agentes (BaseAgent)."""

    def chat(self, tier: ModelTier = ..., temperature: float = ...) -> BaseChatModel: ...

    def contar_tokens(self, texto: str) -> int: ...


def get_llm_factory(settings: Settings | None = None) -> LLMFactory:
    """Escolhe a fábrica conforme `LLM_PROVIDER` ("azure" | "anthropic")."""
    settings = settings or get_settings()
    if settings.llm_provider.lower() == "anthropic":
        # Import tardio: só carrega langchain-anthropic quando de fato usado.
        from app.services.llm.claude_client import ClaudeLLMFactory

        return ClaudeLLMFactory(settings)
    return AzureLLMFactory(settings)
