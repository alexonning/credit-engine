"""Decision Engine: consolida os resultados dos agentes numa decisao final.

Regras de agregacao (deterministicas):
  - Qualquer BLOCKER reprovado -> DENIED.
  - Nenhum blocker, mas ha WARNING reprovado -> REVIEW (analise/negociacao).
  - Tudo ok -> APPROVED.
O score final e a media ponderada dos scores dos agentes.
"""
from __future__ import annotations

from decimal import Decimal

from app.schemas.credit import (
    AgentResult,
    Decision,
    RuleFinding,
    Severity,
)


# peso de cada agente no score consolidado
AGENT_WEIGHTS: dict[str, float] = {
    "regras_sistemicas": 0.35,
    "regras_internas": 0.25,
    "concessao": 0.25,
    "produto": 0.15,
}


def _all_findings(results: list[AgentResult]) -> list[RuleFinding]:
    return [f for r in results for f in r.findings]


def consolidate(results: list[AgentResult]) -> tuple[Decision, float]:
    findings = _all_findings(results)

    has_blocker = any(f for f in findings if not f.passed and f.severity == Severity.BLOCKER)
    has_warning = any(f for f in findings if not f.passed and f.severity == Severity.WARNING)

    if has_blocker:
        decision = Decision.DENIED
    elif has_warning:
        decision = Decision.REVIEW
    else:
        decision = Decision.APPROVED

    total_weight = sum(AGENT_WEIGHTS.get(r.agent, 0.1) for r in results) or 1.0
    weighted = sum(r.score * AGENT_WEIGHTS.get(r.agent, 0.1) for r in results)
    score = round(weighted / total_weight, 4)

    return decision, score


def approved_amount(requested: Decimal, decision: Decision, score: float) -> Decimal | None:
    """Define o valor aprovado. Em REVIEW pode oferecer valor parcial."""
    if decision == Decision.DENIED:
        return None
    if decision == Decision.APPROVED:
        return requested
    # REVIEW: aprova proporcional ao score (min 40%, max 90% do solicitado)
    factor = max(0.4, min(0.9, score))
    return (requested * Decimal(str(round(factor, 2)))).quantize(Decimal("0.01"))
