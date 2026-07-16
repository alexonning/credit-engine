"""Agente de Regras Internas (apetite de risco da instituicao)."""
from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent, base_score
from app.schemas.credit import RuleFinding


class RegrasInternasAgent(BaseAgent):
    name = "regras_internas"
    category = "interna"
    system_prompt = (
        "Voce e especialista nas politicas internas de risco da instituicao. "
        "Explique de forma objetiva a aderencia ao apetite de risco interno."
    )

    def _score(self, ctx: dict[str, Any], findings: list[RuleFinding]) -> float:
        return base_score(findings)
