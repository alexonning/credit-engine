"""Aplicação FastAPI: bootstrap, lifespan e wiring de dependências."""
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.api.middlewares.request_logging import RequestLoggingMiddleware
from app.api.routers.credit_analysis import router as credit_router
from app.config.settings import get_settings
from app.database.session import unit_of_work
from app.orchestrator.graph import AnaliseOrchestrator
from app.repositories.credit_analysis import RuleRepository
from app.services.llm.factory import get_llm_factory
from app.utils.logging import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    async with unit_of_work() as session:
        regras = await RuleRepository(session).carregar_regras_ativas()
    logger.info("regras_carregadas", quantidade=len(regras))
    app.state.orchestrator = AnaliseOrchestrator(
        llm_factory=get_llm_factory(settings),
        regras_vigentes=regras,
    )
    yield
    logger.info("aplicacao_encerrando")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Credit Engine",
        version="0.1.0",
        description="Motor de análise de crédito corporativo baseado em IA",
        lifespan=lifespan,
    )
    app.add_middleware(RequestLoggingMiddleware)
    app.include_router(credit_router)

    @app.get("/health", tags=["infra"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
