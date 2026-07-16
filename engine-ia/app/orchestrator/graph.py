"""Construcao do grafo de orquestracao com LangGraph.

Fluxo:

    cadastro
       |
       +--> regras_sistemicas --+
       +--> regras_internas  ---+--> decision --> negociacao --> explicabilidade --> END
       +--> concessao       ----+
       +--> produto         ----+

Os quatro agentes de analise rodam em paralelo (fan-out a partir do cadastro),
convergem no no 'decision' (fan-in) e o resultado e enriquecido por negociacao e
explicabilidade. O Decision Engine e o Rule Engine sao deterministicos.
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents.cadastro import CadastroAgent
from app.agents.concessao import ConcessaoAgent
from app.agents.explicabilidade import ExplicabilidadeAgent
from app.agents.negociacao import NegociacaoAgent
from app.agents.produto import ProdutoAgent
from app.agents.regras_internas import RegrasInternasAgent
from app.agents.regras_sistemicas import RegrasSistemicasAgent
from app.config import settings
from app.core.logging import get_logger
from app.engine import decision_engine
from app.engine.rule_engine import RuleEngine
from app.llm.azure_client import get_llm
from app.orchestrator.state import CreditState
from app.schemas.credit import Decision

logger = get_logger("orchestrator")


def build_graph(include_explanation: bool = True):
    """Monta o grafo. Com include_explanation=False, encerra apos a negociacao
    (usado no fluxo de streaming, onde a explicacao e gerada em fluxo separado)."""
    rule_engine = RuleEngine.from_dir(settings.rules_dir)
    llm = get_llm()

    cadastro = CadastroAgent(rule_engine, llm)
    sistemicas = RegrasSistemicasAgent(rule_engine, llm)
    internas = RegrasInternasAgent(rule_engine, llm)
    concessao = ConcessaoAgent(rule_engine, llm)
    produto = ProdutoAgent(rule_engine, llm)
    negociacao = NegociacaoAgent()
    explicabilidade = ExplicabilidadeAgent(llm)

    # --- nos ---
    def node_cadastro(state: CreditState) -> dict:
        result = cadastro.run(state["ctx"])
        logger.info("agent_done", agent="cadastro", decision=result.decision.value)
        return {"agent_results": [result]}

    def node_sistemicas(state: CreditState) -> dict:
        result = sistemicas.run(state["ctx"])
        logger.info("agent_done", agent="regras_sistemicas", decision=result.decision.value)
        return {"agent_results": [result]}

    def node_internas(state: CreditState) -> dict:
        result = internas.run(state["ctx"])
        logger.info("agent_done", agent="regras_internas", decision=result.decision.value)
        return {"agent_results": [result]}

    def node_concessao(state: CreditState) -> dict:
        result = concessao.run(state["ctx"])
        logger.info("agent_done", agent="concessao", decision=result.decision.value)
        return {"agent_results": [result]}

    def node_produto(state: CreditState) -> dict:
        result = produto.run(state["ctx"])
        logger.info("agent_done", agent="produto", decision=result.decision.value)
        return {"agent_results": [result]}

    def node_decision(state: CreditState) -> dict:
        results = state["agent_results"]
        # o agente de cadastro pode reprovar por dados invalidos
        cadastro_result = next((r for r in results if r.agent == "cadastro"), None)
        if cadastro_result and cadastro_result.decision == Decision.DENIED:
            decision, score = Decision.DENIED, cadastro_result.score
        else:
            analysis = [r for r in results if r.agent != "cadastro"]
            decision, score = decision_engine.consolidate(analysis)

        amount = decision_engine.approved_amount(
            state["request"].product.amount, decision, score
        )
        logger.info("decision_consolidated", decision=decision.value, score=score)
        return {"decision": decision, "score": score, "approved_amount": amount}

    def node_negociacao(state: CreditState) -> dict:
        offer = negociacao.make_offer(
            state["ctx"], state["decision"], state["score"], state["approved_amount"]
        )
        return {"offer": offer}

    def node_explicabilidade(state: CreditState) -> dict:
        explanation = explicabilidade.explain(
            state["decision"], state["score"], state["agent_results"]
        )
        return {"explanation": explanation}

    # --- montagem do grafo ---
    graph = StateGraph(CreditState)
    graph.add_node("cadastro", node_cadastro)
    graph.add_node("regras_sistemicas", node_sistemicas)
    graph.add_node("regras_internas", node_internas)
    graph.add_node("concessao", node_concessao)
    graph.add_node("produto", node_produto)
    graph.add_node("decision_engine", node_decision)
    graph.add_node("negociacao", node_negociacao)

    graph.add_edge(START, "cadastro")
    # fan-out: cadastro dispara os 4 agentes de analise em paralelo
    for n in ("regras_sistemicas", "regras_internas", "concessao", "produto"):
        graph.add_edge("cadastro", n)
        graph.add_edge(n, "decision_engine")  # fan-in
    graph.add_edge("decision_engine", "negociacao")

    if include_explanation:
        graph.add_node("explicabilidade", node_explicabilidade)
        graph.add_edge("negociacao", "explicabilidade")
        graph.add_edge("explicabilidade", END)
    else:
        graph.add_edge("negociacao", END)

    return graph.compile()


# grafos compilados (reutilizados entre requests), um por variante
_compiled: dict[bool, object] = {}


def get_graph(include_explanation: bool = True):
    if include_explanation not in _compiled:
        _compiled[include_explanation] = build_graph(include_explanation)
    return _compiled[include_explanation]
