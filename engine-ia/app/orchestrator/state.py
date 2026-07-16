"""Estado compartilhado do grafo de orquestracao (LangGraph)."""
from __future__ import annotations

import operator
from decimal import Decimal
from typing import Annotated, Any, TypedDict

from app.schemas.credit import (
    AgentResult,
    CreditRequest,
    Decision,
    NegotiationOffer,
)


class CreditState(TypedDict, total=False):
    request_id: str
    request: CreditRequest
    ctx: dict[str, Any]

    # 'operator.add' faz o LangGraph concatenar as listas produzidas pelos
    # nos que rodam em paralelo (fan-in), sem sobrescrever.
    agent_results: Annotated[list[AgentResult], operator.add]

    decision: Decision
    score: float
    approved_amount: Decimal | None
    offer: NegotiationOffer | None
    explanation: str
