"""Estado compartilhado do grafo de análise (LangGraph)."""
from typing import Any, TypedDict

from app.decision_engine.engine import DecisaoFinal, ParecerAgente
from app.rule_engine.models import ResultadoRegra


class AnaliseState(TypedDict, total=False):
    analysis_id: str
    contexto: dict[str, Any]            # fatos normalizados (cliente, proposta, scores)
    pareceres: list[ParecerAgente]      # pareceres acumulados dos agentes
    resultados_regras: list[ResultadoRegra]
    decisao: DecisaoFinal
    explicacao: str                     # texto final para o analista/cooperado
    erros: list[str]
