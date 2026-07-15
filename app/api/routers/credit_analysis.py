"""Endpoint principal de análise de crédito."""
from uuid import UUID, uuid4

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import UsuarioAtual, usuario_atual
from app.database.models import AuditLogORM, CreditAnalysisORM, CustomerORM
from app.database.session import get_session
from app.orchestrator.graph import AnaliseOrchestrator
from app.orchestrator.state import AnaliseState
from app.schemas.credit_analysis import AnaliseCreditoRequest, AnaliseCreditoResponse
from app.utils.logging import get_logger

router = APIRouter(prefix="/api/v1/credit-analysis", tags=["credit-analysis"])
logger = get_logger(__name__)


def get_orchestrator(request: Request) -> AnaliseOrchestrator:
    orchestrator = getattr(request.app.state, "orchestrator", None)
    if orchestrator is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Orquestrador não inicializado",
        )
    return orchestrator  # type: ignore[no-any-return]


@router.post("", response_model=AnaliseCreditoResponse, status_code=status.HTTP_201_CREATED)
async def analisar_credito(
    payload: AnaliseCreditoRequest,
    usuario: UsuarioAtual = Depends(usuario_atual),
    session: AsyncSession = Depends(get_session),
    orchestrator: AnaliseOrchestrator = Depends(get_orchestrator),
) -> AnaliseCreditoResponse:
    analysis_id: UUID = uuid4()
    structlog.contextvars.bind_contextvars(analysis_id=str(analysis_id), usuario=usuario.sub)
    try:
        contexto = {
            "cliente": payload.cliente.model_dump(mode="json"),
            "proposta": payload.proposta.model_dump(mode="json"),
        }
        estado_inicial: AnaliseState = {
            "analysis_id": str(analysis_id),
            "contexto": contexto,
        }
        estado_final = await orchestrator.executar(estado_inicial)
        decisao = estado_final["decisao"]

        # Persistência + auditoria na mesma transação (Unit of Work do get_session)
        cliente_orm = CustomerORM(
            documento="".join(ch for ch in payload.cliente.documento if ch.isdigit()),
            nome=payload.cliente.nome,
            dados=payload.cliente.model_dump(mode="json"),
        )
        session.add(cliente_orm)
        await session.flush()
        session.add(
            CreditAnalysisORM(
                id=analysis_id,
                customer_id=cliente_orm.id,
                produto_codigo=payload.proposta.produto_codigo,
                contexto=contexto,
                decisao=decisao.resultado.value,
                motivos=decisao.motivos,
                regras_disparadas=decisao.regras_disparadas,
                explicacao=estado_final["explicacao"],
            )
        )
        session.add(
            AuditLogORM(
                analysis_id=analysis_id,
                usuario=usuario.sub,
                evento="ANALISE_CONCLUIDA",
                detalhes={"decisao": decisao.resultado.value,
                          "regras": decisao.regras_disparadas},
            )
        )

        return AnaliseCreditoResponse(
            analysis_id=analysis_id,
            decisao=decisao.resultado,
            motivos=decisao.motivos,
            restricoes=decisao.restricoes,
            documentos_pendentes=decisao.documentos_pendentes,
            garantias_exigidas=decisao.garantias_exigidas,
            regras_disparadas=decisao.regras_disparadas,
            permite_contraproposta=decisao.permite_contraproposta,
            explicacao=estado_final["explicacao"],
        )
    finally:
        structlog.contextvars.unbind_contextvars("analysis_id", "usuario")
