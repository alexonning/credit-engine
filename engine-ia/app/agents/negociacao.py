"""Agente de Negociacao: monta uma contraproposta quando a decisao e REVIEW.

Deterministico: define valor aprovado, prazo e taxa de juros com base no score
e no comprometimento de renda. Nao depende do LLM.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.schemas.credit import Decision, NegotiationOffer


class NegociacaoAgent:
    name = "negociacao"

    def make_offer(
        self,
        ctx: dict[str, Any],
        decision: Decision,
        score: float,
        approved_amount: Decimal | None,
    ) -> NegotiationOffer | None:
        if decision == Decision.DENIED or approved_amount is None:
            return None

        # Taxa de juros anual em funcao do score: melhor score -> menor taxa.
        # Faixa: 0.18 (score alto) ate 0.42 (score baixo).
        annual_rate = round(0.42 - (0.24 * score), 4)

        conditions: list[str] = []
        term = int(ctx.get("term_months", 12))

        if decision == Decision.REVIEW:
            conditions.append("Valor ajustado conforme analise de risco.")
            if ctx.get("dti", 0) > 0.5:
                # alonga o prazo para reduzir a parcela
                term = min(int(term * 1.5), 84)
                conditions.append(f"Prazo estendido para {term} meses para reduzir a parcela.")

        conditions.append(f"Taxa de juros de {annual_rate * 100:.2f}% a.a.")

        return NegotiationOffer(
            approved_amount=approved_amount,
            term_months=term,
            interest_rate=annual_rate,
            conditions=conditions,
        )
