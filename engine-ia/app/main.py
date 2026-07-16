"""Entrypoint da aplicacao FastAPI."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import credit, health
from app.config import settings
from app.core.logging import configure_logging, get_logger
from app.db.session import init_db

configure_logging()
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup", app=settings.app_name, env=settings.app_env)
    init_db()
    yield
    logger.info("shutdown")


app = FastAPI(
    title="Credit Analysis Engine",
    description="Agente de IA multi-agente para analise de credito.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router, prefix=settings.api_prefix)
app.include_router(credit.router, prefix=settings.api_prefix)


@app.get("/")
def root() -> dict:
    return {
        "service": settings.app_name,
        "docs": "/docs",
        "analyze": f"{settings.api_prefix}/credit/analyze",
    }
