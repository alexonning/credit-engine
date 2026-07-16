"""Fábrica de clientes Claude (Anthropic) — alternativa à AzureLLMFactory.

Espelha a interface pública de `AzureLLMFactory` (`chat`, `contar_tokens`) para
funcionar como drop-in: os agentes (BaseAgent) dependem de
`.with_structured_output(...)`, suportado igualmente por `ChatAnthropic`.
Usa a integração oficial `langchain-anthropic` (fala com a API real da
Anthropic — não é um shim compatível com OpenAI).
"""
from functools import lru_cache

from anthropic import Anthropic
from langchain_anthropic import ChatAnthropic

from app.config.settings import Settings, get_settings
from app.services.llm.azure_client import ModelTier
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ClaudeLLMFactory:
    """Cria clientes LangChain para a API da Anthropic (Claude).

    Mapeia os tiers usados pelos agentes (nomeados a partir do provedor Azure)
    para modelos Claude configuráveis via ambiente:
      - "gpt-4.1-mini"  -> ANTHROPIC_MODEL_PRINCIPAL (padrão: claude-sonnet-5)
      - "gpt-4.1"       -> ANTHROPIC_MODEL_FALLBACK  (padrão: claude-opus-4-8)

    Assim o BaseAgent (que pede `tier_principal`/`tier_fallback`) permanece
    inalterado ao trocar de provedor.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def _modelo_para_tier(self, tier: ModelTier) -> str:
        if tier == "gpt-4.1":
            return self._settings.anthropic_model_fallback
        return self._settings.anthropic_model_principal

    def chat(
        self, tier: ModelTier = "gpt-4.1-mini", temperature: float | None = None
    ) -> ChatAnthropic:
        # IMPORTANTE: Claude Opus 4.8 / Sonnet 5 REJEITAM parâmetros de sampling
        # (temperature/top_p/top_k) com HTTP 400. O determinismo, quando exigido,
        # é obtido por prompt — não por temperature=0. Por isso não repassamos
        # `temperature` ao cliente; o parâmetro existe só por paridade de assinatura.
        if temperature is not None:
            logger.warning(
                "temperature_ignorada_claude",
                motivo="Opus 4.8 / Sonnet 5 não aceitam parâmetros de sampling",
            )
        return ChatAnthropic(
            model=self._modelo_para_tier(tier),
            api_key=self._settings.anthropic_api_key,  # type: ignore[arg-type]
            timeout=self._settings.anthropic_timeout_seconds,
            max_retries=self._settings.anthropic_max_retries,
            max_tokens=self._settings.anthropic_max_tokens,
        )

    def embeddings(self) -> None:
        raise NotImplementedError(
            "A Anthropic não oferece API de embeddings. Mantenha embeddings no "
            "provedor Azure (AzureLLMFactory.embeddings) ou use um provedor "
            "dedicado (ex.: Voyage AI)."
        )

    def contar_tokens(self, texto: str) -> int:
        """Conta tokens via endpoint oficial da Anthropic (`count_tokens`).

        Não usa `tiktoken` (que subestima tokens da Claude). Faz fallback para
        uma estimativa local caso a chamada falhe — a contagem alimenta apenas
        logs de auditoria e nunca deve derrubar a análise.
        """
        try:
            client = _anthropic_client(self._settings.anthropic_api_key)
            resposta = client.messages.count_tokens(
                model=self._settings.anthropic_model_principal,
                messages=[{"role": "user", "content": texto}],
            )
            return resposta.input_tokens
        except Exception as exc:  # noqa: BLE001 - logging não pode quebrar o fluxo
            logger.warning("contar_tokens_fallback", erro=str(exc))
            return len(texto) // 4


@lru_cache(maxsize=1)
def _anthropic_client(api_key: str) -> Anthropic:
    """Cliente Anthropic cacheado por processo (usado só para count_tokens)."""
    return Anthropic(api_key=api_key)
