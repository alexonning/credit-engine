"""Fábrica de clientes Azure OpenAI com retry, timeout e contagem de tokens."""
from typing import Literal

import tiktoken
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings

from app.config.settings import Settings, get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

ModelTier = Literal["gpt-4.1", "gpt-4.1-mini"]


class AzureLLMFactory:
    """Cria clientes LangChain para Azure OpenAI.

    Fallback: se o tier principal falhar após os retries, o chamador pode
    solicitar o tier alternativo via `chat(tier=...)` — a política de
    fallback fica no BaseAgent para manter esta fábrica sem estado.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def chat(self, tier: ModelTier = "gpt-4.1-mini", temperature: float = 0.0) -> AzureChatOpenAI:
        deployment = (
            self._settings.azure_openai_deployment_gpt41
            if tier == "gpt-4.1"
            else self._settings.azure_openai_deployment_gpt41_mini
        )
        return AzureChatOpenAI(
            azure_endpoint=self._settings.azure_openai_endpoint,
            api_key=self._settings.azure_openai_api_key,  # type: ignore[arg-type]
            api_version=self._settings.azure_openai_api_version,
            azure_deployment=deployment,
            temperature=temperature,
            timeout=self._settings.azure_openai_timeout_seconds,
            max_retries=self._settings.azure_openai_max_retries,
        )

    def embeddings(self) -> AzureOpenAIEmbeddings:
        return AzureOpenAIEmbeddings(
            azure_endpoint=self._settings.azure_openai_endpoint,
            api_key=self._settings.azure_openai_api_key,  # type: ignore[arg-type]
            api_version=self._settings.azure_openai_api_version,
            azure_deployment=self._settings.azure_openai_deployment_embeddings,
        )

    @staticmethod
    def contar_tokens(texto: str, encoding_name: str = "o200k_base") -> int:
        encoding = tiktoken.get_encoding(encoding_name)
        return len(encoding.encode(texto))
