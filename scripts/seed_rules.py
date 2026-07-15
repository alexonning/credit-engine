"""Seed de regras iniciais (exemplo real de política de crédito).

Uso: python -m scripts.seed_rules
Insere regras versionadas na base; idempotente por código de regra.
"""
import asyncio

from sqlalchemy import select

from app.database.models import RuleORM, RuleVersionORM
from app.database.session import unit_of_work
from app.domain.enums import RuleAction, RuleCriticality, RuleType
from app.domain.value_objects import Vigencia
from app.rule_engine.models import Condicao, GrupoCondicoes, Operador, Regra

REGRAS_INICIAIS: list[Regra] = [
    Regra(
        codigo="SIS-001-SCORE-MINIMO",
        nome="Score mínimo de bureau",
        descricao="Bloqueia propostas com score de bureau abaixo do mínimo institucional.",
        tipo=RuleType.SISTEMICA,
        categoria="score",
        criticidade=RuleCriticality.CRITICA,
        acao=RuleAction.BLOQUEAR,
        prioridade=1000,
        vigencia=Vigencia(inicio="2026-01-01"),
        explicacao="Score de crédito abaixo do mínimo exigido pela política institucional (300).",
        quando=GrupoCondicoes(condicoes=[
            Condicao(campo="cliente.score_bureau", operador=Operador.LT, valor=300),
        ]),
    ),
    Regra(
        codigo="INT-001-COMPROMETIMENTO",
        nome="Comprometimento de renda",
        descricao="Exige garantia quando a parcela estimada supera 30% da renda mensal.",
        tipo=RuleType.INTERNA,
        categoria="capacidade_pagamento",
        criticidade=RuleCriticality.ALTA,
        acao=RuleAction.EXIGIR_GARANTIA,
        prioridade=800,
        vigencia=Vigencia(inicio="2026-01-01"),
        explicacao="Parcela estimada compromete mais de 30% da renda mensal declarada.",
        garantia_exigida="Garantia real (alienação fiduciária ou hipoteca) ou avalista",
        quando=GrupoCondicoes(condicoes=[
            Condicao(campo="derivados.comprometimento_renda_pct", operador=Operador.GT, valor=30),
        ]),
    ),
    Regra(
        codigo="INT-002-RELACIONAMENTO-CURTO",
        nome="Relacionamento recente",
        descricao="Restringe valor para cooperados com menos de 6 meses de relacionamento.",
        tipo=RuleType.INTERNA,
        categoria="relacionamento",
        criticidade=RuleCriticality.MEDIA,
        acao=RuleAction.RESTRINGIR,
        prioridade=500,
        vigencia=Vigencia(inicio="2026-01-01"),
        explicacao="Cooperado com menos de 6 meses de relacionamento: limite reduzido a 50% do teto do produto.",
        quando=GrupoCondicoes(condicoes=[
            Condicao(campo="cliente.tempo_relacionamento_meses", operador=Operador.LT, valor=6),
        ]),
    ),
]


async def main() -> None:
    async with unit_of_work() as session:
        for regra in REGRAS_INICIAIS:
            existente = await session.scalar(
                select(RuleORM).where(RuleORM.codigo == regra.codigo)
            )
            if existente is not None:
                continue
            session.add(RuleORM(codigo=regra.codigo, versao_atual=regra.versao, ativa=True))
            session.add(
                RuleVersionORM(
                    rule_codigo=regra.codigo,
                    versao=regra.versao,
                    definicao=regra.model_dump(mode="json"),
                    criado_por="seed",
                )
            )
    print(f"Seed concluído: {len(REGRAS_INICIAIS)} regras processadas.")


if __name__ == "__main__":
    asyncio.run(main())
