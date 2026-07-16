"""Agente de Produto (regras especificas de cada produto de credito)."""
from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent, base_score
from app.schemas.credit import RuleFinding


class ProdutoAgent(BaseAgent):
    name = "produto"
    category = "produto"
    system_prompt = (
        "Voce e especialista nas regras especificas por produto de credito "
        "(CDC, Consignado, Cartao, Home Equity). Explique de forma objetiva."
    )

    def _score(self, ctx: dict[str, Any], findings: list[RuleFinding]) -> float:
        return base_score(findings)
