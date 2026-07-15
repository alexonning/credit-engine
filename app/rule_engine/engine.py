"""Avaliador determinístico de regras.

Sem LLM, sem I/O: recebe regras + contexto de fatos e devolve resultados
estruturados. Isso garante reprodutibilidade e auditabilidade total.
"""
from datetime import UTC, datetime
from typing import Any

from app.rule_engine.models import Condicao, GrupoCondicoes, Operador, Regra, ResultadoRegra
from app.utils.logging import get_logger

logger = get_logger(__name__)


class RuleEngineError(Exception):
    """Erro de avaliação de regra (campo inexistente, operador inválido, etc.)."""


class RuleEngine:
    def avaliar(
        self,
        regras: list[Regra],
        contexto: dict[str, Any],
        produto_codigo: str,
        data_referencia: datetime | None = None,
    ) -> list[ResultadoRegra]:
        """Avalia todas as regras vigentes aplicáveis ao produto."""
        ref = (data_referencia or datetime.now(UTC)).date().isoformat()
        aplicaveis = [
            r for r in regras
            if self._vigente(r, ref) and (r.produto_codigo is None or r.produto_codigo == produto_codigo)
        ]
        resultados: list[ResultadoRegra] = []
        for regra in sorted(aplicaveis, key=lambda r: r.prioridade, reverse=True):
            disparou = self._avaliar_grupo(regra.quando, contexto, regra.codigo)
            resultados.append(
                ResultadoRegra(
                    codigo=regra.codigo,
                    nome=regra.nome,
                    versao=regra.versao,
                    disparou=disparou,
                    acao=regra.acao,
                    criticidade=regra.criticidade,
                    prioridade=regra.prioridade,
                    explicacao=regra.explicacao,
                    documento_exigido=regra.documento_exigido,
                    garantia_exigida=regra.garantia_exigida,
                )
            )
            logger.info(
                "regra_avaliada",
                regra=regra.codigo,
                versao=regra.versao,
                disparou=disparou,
            )
        return resultados

    @staticmethod
    def _vigente(regra: Regra, data_iso: str) -> bool:
        if data_iso < regra.vigencia.inicio:
            return False
        return regra.vigencia.fim is None or data_iso <= regra.vigencia.fim

    def _avaliar_grupo(
        self, grupo: GrupoCondicoes, contexto: dict[str, Any], regra_codigo: str
    ) -> bool:
        avaliacoes = [
            self._avaliar_grupo(c, contexto, regra_codigo)
            if isinstance(c, GrupoCondicoes)
            else self._avaliar_condicao(c, contexto, regra_codigo)
            for c in grupo.condicoes
        ]
        return all(avaliacoes) if grupo.logica == "AND" else any(avaliacoes)

    def _avaliar_condicao(
        self, cond: Condicao, contexto: dict[str, Any], regra_codigo: str
    ) -> bool:
        atual = self._resolver_campo(cond.campo, contexto, regra_codigo)
        esperado = cond.valor
        match cond.operador:
            case Operador.EQ:
                return bool(atual == esperado)
            case Operador.NE:
                return bool(atual != esperado)
            case Operador.GT:
                return bool(atual > esperado)
            case Operador.GTE:
                return bool(atual >= esperado)
            case Operador.LT:
                return bool(atual < esperado)
            case Operador.LTE:
                return bool(atual <= esperado)
            case Operador.IN:
                return atual in esperado
            case Operador.NOT_IN:
                return atual not in esperado
            case Operador.BETWEEN:
                minimo, maximo = esperado
                return bool(minimo <= atual <= maximo)
        raise RuleEngineError(f"Operador não suportado: {cond.operador}")

    @staticmethod
    def _resolver_campo(campo: str, contexto: dict[str, Any], regra_codigo: str) -> Any:
        atual: Any = contexto
        for parte in campo.split("."):
            if not isinstance(atual, dict) or parte not in atual:
                raise RuleEngineError(
                    f"Campo '{campo}' ausente no contexto (regra {regra_codigo})"
                )
            atual = atual[parte]
        return atual
