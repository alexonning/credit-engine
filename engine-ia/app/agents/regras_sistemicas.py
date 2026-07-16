"""Agente de Regras Sistemicas (compliance, bureau, politicas do sistema)."""
from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent, base_score
from app.schemas.credit import RuleFinding


class RegrasSistemicasAgent(BaseAgent):
    name = "regras_sistemicas"
    category = "sistemica"
    system_prompt = (
        "Voce e especialista em regras sistemicas e compliance de credito. "
        "Explique de forma objetiva por que a politica sistemica foi ou nao atendida."
    )

    def _score(self, ctx: dict[str, Any], findings: list[RuleFinding]) -> float:
        return base_score(findings)
