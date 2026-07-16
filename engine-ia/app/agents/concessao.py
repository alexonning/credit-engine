"""Agente de Concessao (limites e condicoes do ato de conceder)."""
from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent, base_score
from app.schemas.credit import RuleFinding


class ConcessaoAgent(BaseAgent):
    name = "concessao"
    category = "concessao"
    system_prompt = (
        "Voce e especialista em regras de concessao de credito (limites, prazos, "
        "comprometimento de renda). Explique a decisao de forma objetiva."
    )

    def _score(self, ctx: dict[str, Any], findings: list[RuleFinding]) -> float:
        return base_score(findings)
