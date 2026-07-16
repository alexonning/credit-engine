"""Grafo LangGraph de orquestração da análise de crédito.

Fase 1 do fluxo completo:
  validar → cadastro → regras → decisão → explicação

Os nós de RegraSistemica/RegraInterna/Produto/Concessao/Compliance/Negociacao
seguem o mesmo contrato (ParecerAgente) e são plugados como novos nós entre
`cadastro` e `regras` sem alterar o Decision Engine.
"""
from typing import Any

from langgraph.graph import END, StateGraph

from app.agents.cadastro.agent import CadastroAgent
from app.agents.cadastro.service import CadastroService
from app.decision_engine.engine import DecisionEngine
from app.orchestrator.state import AnaliseState
from app.rule_engine.engine import RuleEngine
from app.rule_engine.models import Regra
from app.services.llm.factory import LLMFactory
from app.utils.logging import get_logger

logger = get_logger(__name__)


class AnaliseOrchestrator:
    def __init__(
        self,
        llm_factory: LLMFactory,
        regras_vigentes: list[Regra],
    ) -> None:
        self._cadastro = CadastroService(CadastroAgent(llm_factory))
        self._rule_engine = RuleEngine()
        self._decision_engine = DecisionEngine()
        self._regras = regras_vigentes
        self._graph = self._construir()

    def _construir(self) -> Any:
        g: StateGraph = StateGraph(AnaliseState)
        g.add_node("validar", self._no_validar)
        g.add_node("cadastro", self._no_cadastro)
        g.add_node("regras", self._no_regras)
        g.add_node("decisao", self._no_decisao)
        g.add_node("explicacao", self._no_explicacao)

        g.set_entry_point("validar")
        g.add_edge("validar", "cadastro")
        g.add_edge("cadastro", "regras")
        g.add_edge("regras", "decisao")
        g.add_edge("decisao", "explicacao")
        g.add_edge("explicacao", END)
        return g.compile()

    async def executar(self, state: AnaliseState) -> AnaliseState:
        logger.info("analise_iniciada", analysis_id=state.get("analysis_id"))
        resultado: AnaliseState = await self._graph.ainvoke(state)
        logger.info(
            "analise_concluida",
            analysis_id=state.get("analysis_id"),
            decisao=resultado["decisao"].resultado.value,
        )
        return resultado

    # ------------------------------------------------------------------ nós

    async def _no_validar(self, state: AnaliseState) -> AnaliseState:
        contexto = state.get("contexto", {})
        faltando = [c for c in ("cliente", "proposta") if c not in contexto]
        if faltando:
            raise ValueError(f"Contexto inválido: seções ausentes {faltando}")
        return {"pareceres": [], "erros": []}

    async def _no_cadastro(self, state: AnaliseState) -> AnaliseState:
        parecer = await self._cadastro.analisar(state["contexto"])
        return {"pareceres": [*state["pareceres"], parecer]}

    async def _no_regras(self, state: AnaliseState) -> AnaliseState:
        contexto = state["contexto"]
        resultados = self._rule_engine.avaliar(
            regras=self._regras,
            contexto=contexto,
            produto_codigo=contexto["proposta"]["produto_codigo"],
        )
        return {"resultados_regras": resultados}

    async def _no_decisao(self, state: AnaliseState) -> AnaliseState:
        decisao = self._decision_engine.decidir(
            pareceres=state["pareceres"],
            resultados_regras=state["resultados_regras"],
        )
        return {"decisao": decisao}

    async def _no_explicacao(self, state: AnaliseState) -> AnaliseState:
        """Explicação determinística baseada na decisão consolidada.

        (Na fase 2, o ExplicacaoAgent reescreve este texto para o cooperado
        via LLM — a versão determinística permanece como registro auditável.)
        """
        d = state["decisao"]
        linhas = [f"Resultado da análise: {d.resultado.value}"]
        if d.motivos:
            linhas.append("Motivos:")
            linhas.extend(f"  - {m}" for m in d.motivos)
        if d.documentos_pendentes:
            linhas.append("Documentos pendentes:")
            linhas.extend(f"  - {doc}" for doc in d.documentos_pendentes)
        if d.garantias_exigidas:
            linhas.append("Garantias exigidas:")
            linhas.extend(f"  - {g}" for g in d.garantias_exigidas)
        if d.regras_disparadas:
            linhas.append(f"Regras aplicadas: {', '.join(d.regras_disparadas)}")
        return {"explicacao": "\n".join(linhas)}
