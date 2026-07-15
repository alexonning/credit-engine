"""Modelos do Rule Engine: regras parametrizadas, versionadas e determinísticas.

O Rule Engine NÃO depende de LLM. As regras são persistidas em banco
(tabelas rules / rule_versions) e avaliadas contra um contexto de fatos.
"""
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.domain.enums import RuleAction, RuleCriticality, RuleType
from app.domain.value_objects import Vigencia


class Operador(StrEnum):
    EQ = "eq"
    NE = "ne"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    IN = "in"
    NOT_IN = "not_in"
    BETWEEN = "between"


class Condicao(BaseModel):
    """Condição atômica avaliada contra o contexto de fatos.

    `campo` usa dot-notation para navegar no contexto,
    ex.: "cliente.melhor_score", "proposta.prazo_meses".
    """
    campo: str
    operador: Operador
    valor: Any


class GrupoCondicoes(BaseModel):
    """Grupo lógico de condições (AND/OR), com suporte a aninhamento."""
    logica: str = Field(default="AND", pattern="^(AND|OR)$")
    condicoes: list["Condicao | GrupoCondicoes"]


class Regra(BaseModel):
    """Regra de negócio parametrizada.

    A regra "dispara" (é violada) quando suas condições são verdadeiras.
    """
    codigo: str
    nome: str
    descricao: str
    tipo: RuleType
    categoria: str
    criticidade: RuleCriticality
    acao: RuleAction
    prioridade: int = Field(ge=0, le=1000)
    vigencia: Vigencia
    produto_codigo: str | None = None  # None = aplica a todos os produtos
    versao: int = 1
    explicacao: str  # texto exibido ao analista quando a regra dispara
    documento_exigido: str | None = None
    garantia_exigida: str | None = None
    quando: GrupoCondicoes


class ResultadoRegra(BaseModel):
    """Resultado da avaliação de uma regra."""
    codigo: str
    nome: str
    versao: int
    disparou: bool
    acao: RuleAction
    criticidade: RuleCriticality
    prioridade: int
    explicacao: str
    documento_exigido: str | None = None
    garantia_exigida: str | None = None
