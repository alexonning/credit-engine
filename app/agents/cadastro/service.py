"""Serviço de aplicação do CadastroAgent: converte saída em ParecerAgente."""
from typing import Any

from app.agents.cadastro.agent import CadastroAgent
from app.agents.base import AgentExecutionError
from app.decision_engine.engine import ParecerAgente
from app.domain.enums import AgentStatus
from app.utils.logging import get_logger

logger = get_logger(__name__)


class CadastroService:
    def __init__(self, agent: CadastroAgent) -> None:
        self._agent = agent

    async def analisar(self, contexto: dict[str, Any]) -> ParecerAgente:
        try:
            saida = await self._agent.executar(contexto)
        except AgentExecutionError as exc:
            logger.error("cadastro_agent_erro", erro=str(exc))
            return ParecerAgente(
                agente="cadastro",
                status=AgentStatus.ERRO,
                motivos=[f"Falha na análise cadastral automática: {exc}"],
            )
        status = AgentStatus.OK if saida.status == "OK" else AgentStatus.PENDENTE
        return ParecerAgente(
            agente="cadastro",
            status=status,
            motivos=saida.inconsistencias + saida.observacoes,
            documentos_pendentes=saida.pendencias,
            score_ajustado=saida.score_cadastral,
        )
