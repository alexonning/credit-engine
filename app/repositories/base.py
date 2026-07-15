"""Repository genérico (Repository Pattern) sobre AsyncSession."""
from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Base

TModel = TypeVar("TModel", bound=Base)


class BaseRepository(Generic[TModel]):
    model: type[TModel]

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def obter(self, id_: UUID) -> TModel | None:
        return await self._session.get(self.model, id_)

    async def adicionar(self, entidade: TModel) -> TModel:
        self._session.add(entidade)
        await self._session.flush()
        return entidade

    async def listar(self, limite: int = 100) -> list[TModel]:
        resultado = await self._session.execute(select(self.model).limit(limite))
        return list(resultado.scalars().all())
