"""Repositórios específicos do domínio de crédito."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import CreditAnalysisORM, RuleORM, RuleVersionORM
from app.repositories.base import BaseRepository
from app.rule_engine.models import Regra


class CreditAnalysisRepository(BaseRepository[CreditAnalysisORM]):
    model = CreditAnalysisORM


class RuleRepository(BaseRepository[RuleORM]):
    model = RuleORM

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def carregar_regras_ativas(self) -> list[Regra]:
        """Carrega a versão atual de cada regra ativa e desserializa em `Regra`."""
        stmt = (
            select(RuleVersionORM)
            .join(RuleORM, RuleORM.codigo == RuleVersionORM.rule_codigo)
            .where(RuleORM.ativa.is_(True), RuleORM.versao_atual == RuleVersionORM.versao)
        )
        resultado = await self._session.execute(stmt)
        return [Regra.model_validate(rv.definicao) for rv in resultado.scalars().all()]
