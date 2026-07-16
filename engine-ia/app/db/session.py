"""Fabrica de sessoes do SQLAlchemy e inicializacao do schema."""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.core.logging import get_logger
from app.db.models import Base

logger = get_logger("db")

_engine = None
_SessionLocal: sessionmaker | None = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
    return _engine


def get_session_factory() -> sessionmaker:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=_get_engine(), autoflush=False, expire_on_commit=False)
    return _SessionLocal


def init_db() -> None:
    """Cria as tabelas. Em producao prefira Alembic migrations."""
    try:
        Base.metadata.create_all(bind=_get_engine())
        logger.info("db_initialized")
    except Exception as exc:  # noqa: BLE001
        logger.warning("db_init_failed", error=str(exc))


def get_db() -> Generator[Session, None, None]:
    """Dependency do FastAPI: fornece uma sessao por request."""
    factory = get_session_factory()
    db = factory()
    try:
        yield db
    finally:
        db.close()
