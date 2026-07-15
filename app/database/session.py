"""Sessão assíncrona SQLAlchemy 2.0 + Unit of Work."""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config.settings import get_settings

_engine = create_async_engine(str(get_settings().database_url), pool_size=20, max_overflow=10)
_session_factory = async_sessionmaker(_engine, expire_on_commit=False)


@asynccontextmanager
async def unit_of_work() -> AsyncIterator[AsyncSession]:
    """Unit of Work: commit no sucesso, rollback em qualquer exceção."""
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_session() -> AsyncIterator[AsyncSession]:
    """Dependency do FastAPI."""
    async with unit_of_work() as session:
        yield session
