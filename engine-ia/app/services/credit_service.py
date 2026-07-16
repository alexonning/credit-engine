"""Servico de aplicacao: coordena grafo, cache, persistencia e auditoria."""
from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Iterator
from typing import Any

from sqlalchemy.orm import Session

from app.agents.explicabilidade import ExplicabilidadeAgent
from app.cache.redis_client import cache_get, cache_set
from app.core.audit import record_audit
from app.core.logging import get_logger
from app.db.models import CreditDecision
from app.engine.context import build_context
from app.llm.azure_client import get_llm
from app.orchestrator.graph import get_graph
from app.schemas.credit import CreditRequest, CreditResponse

logger = get_logger("credit_service")


def _cache_key(request: CreditRequest) -> str:
    raw = request.model_dump_json().encode("utf-8")
    return "credit:decision:" + hashlib.sha256(raw).hexdigest()


def analyze_credit(request: CreditRequest, db: Session | None = None) -> CreditResponse:
    request_id = uuid.uuid4().hex
    key = _cache_key(request)

    cached = cache_get(key)
    if cached:
        logger.info("cache_hit", request_id=request_id)
        resp = CreditResponse.model_validate_json(cached)
        resp.request_id = request_id
        return resp

    ctx = build_context(request)
    record_audit(db, request_id=request_id, stage="context_built", payload=ctx)

    graph = get_graph()
    final_state = graph.invoke(
        {"request_id": request_id, "request": request, "ctx": ctx}
    )

    response = CreditResponse(
        request_id=request_id,
        decision=final_state["decision"],
        score=final_state["score"],
        approved_amount=final_state.get("approved_amount"),
        agent_results=final_state["agent_results"],
        offer=final_state.get("offer"),
        explanation=final_state.get("explanation", ""),
    )

    record_audit(
        db,
        request_id=request_id,
        stage="decision_final",
        decision=response.decision.value,
        payload=response.model_dump(mode="json"),
    )
    _persist(db, request, response)
    cache_set(key, response.model_dump_json())

    return response


def _sse(event: str, data: dict[str, Any]) -> str:
    """Formata um frame Server-Sent Events (SSE)."""
    payload = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event}\ndata: {payload}\n\n"


def analyze_credit_stream(request: CreditRequest, db: Session | None = None) -> Iterator[str]:
    """Versao streaming: emite a decisao imediatamente (evento 'decision') e depois
    a explicacao token-a-token (eventos 'explanation'), fechando com 'done'.

    A decisao continua deterministica e rapida (Rule + Decision Engine); apenas a
    redacao da justificativa pelo LLM e transmitida em fluxo.
    """
    request_id = uuid.uuid4().hex
    ctx = build_context(request)
    record_audit(db, request_id=request_id, stage="context_built", payload=ctx)

    # roda o pipeline ate a negociacao (sem o no de explicabilidade)
    graph = get_graph(include_explanation=False)
    state = graph.invoke({"request_id": request_id, "request": request, "ctx": ctx})

    decision = state["decision"]
    score = state["score"]
    approved = state.get("approved_amount")
    offer = state.get("offer")
    results = state["agent_results"]

    # 1) decisao completa vai primeiro, imediatamente
    meta = {
        "request_id": request_id,
        "decision": decision.value,
        "score": score,
        "approved_amount": str(approved) if approved is not None else None,
        "offer": offer.model_dump(mode="json") if offer else None,
        "agent_results": [r.model_dump(mode="json") for r in results],
    }
    yield _sse("decision", meta)

    # 2) explicacao em fluxo (token a token)
    agent = ExplicabilidadeAgent(get_llm())
    parts: list[str] = []
    for delta in agent.explain_stream(decision, score, results):
        parts.append(delta)
        yield _sse("explanation", {"delta": delta})

    explanation = "".join(parts)

    # 3) persistencia/auditoria da resposta ja completa
    response = CreditResponse(
        request_id=request_id,
        decision=decision,
        score=score,
        approved_amount=approved,
        agent_results=results,
        offer=offer,
        explanation=explanation,
    )
    record_audit(
        db,
        request_id=request_id,
        stage="decision_final",
        decision=decision.value,
        payload=response.model_dump(mode="json"),
    )
    _persist(db, request, response)

    yield _sse("done", {"request_id": request_id})


def _persist(db: Session | None, request: CreditRequest, response: CreditResponse) -> None:
    if db is None:
        return
    try:
        row = CreditDecision(
            request_id=response.request_id,
            document=request.applicant.document,
            product_code=request.product.product_code,
            decision=response.decision.value,
            score=response.score,
            approved_amount=response.approved_amount,
            explanation=response.explanation,
        )
        db.add(row)
        db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("persist_failed", error=str(exc))
        db.rollback()
