"""Endpoint principal de analise de credito."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.credit import CreditRequest, CreditResponse
from app.services.credit_service import analyze_credit, analyze_credit_stream

router = APIRouter(prefix="/credit", tags=["credit"])


@router.post("/analyze", response_model=CreditResponse)
def analyze(request: CreditRequest, db: Session = Depends(get_db)) -> CreditResponse:
    """Executa a analise multi-agente e retorna a decisao consolidada e explicavel."""
    return analyze_credit(request, db=db)


@router.post("/analyze/stream")
def analyze_stream(request: CreditRequest, db: Session = Depends(get_db)) -> StreamingResponse:
    """Mesma analise, porem em streaming (SSE): a decisao chega imediatamente e a
    explicacao do LLM e transmitida token a token. Ideal para UI em tempo real."""
    return StreamingResponse(
        analyze_credit_stream(request, db=db),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
