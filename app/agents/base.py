"""Contrato base de todos os agentes.

Todo agente:
  - carrega prompts versionados de arquivos .md (system/developer/user);
  - retorna SEMPRE um Pydantic model (structured output), nunca texto livre;
  - registra execução (tokens, latência, modelo, versão de prompt);
  - implementa fallback gpt-4.1 → gpt-4.1-mini (ou vice-versa).
"""
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Generic, TypeVar

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.services.llm.azure_client import AzureLLMFactory, ModelTier
from app.utils.logging import get_logger

TOutput = TypeVar("TOutput", bound=BaseModel)

logger = get_logger(__name__)


class AgentExecutionError(Exception):
    """Falha definitiva de execução do agente (após retries e fallback)."""


class BaseAgent(ABC, Generic[TOutput]):
    nome: str
    output_model: type[TOutput]
    tier_principal: ModelTier = "gpt-4.1-mini"
    tier_fallback: ModelTier = "gpt-4.1"
    prompt_version: str = "1.0.0"

    def __init__(self, llm_factory: AzureLLMFactory) -> None:
        self._llm_factory = llm_factory
        self._prompts_dir = Path(__file__).parent / self.nome / "prompts"

    def _carregar_prompt(self, arquivo: str) -> str:
        caminho = self._prompts_dir / arquivo
        if not caminho.exists():
            raise AgentExecutionError(f"Prompt não encontrado: {caminho}")
        return caminho.read_text(encoding="utf-8")

    @abstractmethod
    def montar_user_prompt(self, contexto: dict[str, Any]) -> str:
        """Renderiza o user prompt a partir do contexto da análise."""

    async def executar(self, contexto: dict[str, Any]) -> TOutput:
        inicio = time.perf_counter()
        system = self._carregar_prompt("system_prompt.md")
        developer = self._carregar_prompt("developer_prompt.md")
        user = self.montar_user_prompt(contexto)
        try:
            saida = await self._invocar(system, developer, user, self.tier_principal)
        except Exception as exc_principal:
            logger.warning("agente_fallback", agente=self.nome,
                           tier=self.tier_fallback, erro=str(exc_principal))
            try:
                saida = await self._invocar(system, developer, user, self.tier_fallback)
            except Exception as exc_fallback:
                raise AgentExecutionError(
                    f"Agente {self.nome} falhou nos dois tiers: {exc_fallback}"
                ) from exc_fallback
        duracao_ms = int((time.perf_counter() - inicio) * 1000)
        logger.info(
            "agente_executado",
            agente=self.nome,
            prompt_version=self.prompt_version,
            duracao_ms=duracao_ms,
            tokens_entrada=self._llm_factory.contar_tokens(system + developer + user),
        )
        return saida

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def _invocar(self, system: str, developer: str, user: str, tier: ModelTier) -> TOutput:
        llm = self._llm_factory.chat(tier=tier)
        estruturado = llm.with_structured_output(self.output_model)
        mensagens = [
            SystemMessage(content=f"{system}\n\n---\n\n{developer}"),
            HumanMessage(content=user),
        ]
        resultado = await estruturado.ainvoke(mensagens)
        if not isinstance(resultado, self.output_model):
            raise AgentExecutionError(
                f"Agente {self.nome} retornou tipo inesperado: {type(resultado)}"
            )
        return resultado
