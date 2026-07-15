"""Testes do Rule Engine (100% determinístico, sem I/O)."""
import pytest

from app.domain.enums import RuleAction, RuleCriticality, RuleType
from app.domain.value_objects import Vigencia
from app.rule_engine.engine import RuleEngine, RuleEngineError
from app.rule_engine.models import Condicao, GrupoCondicoes, Operador, Regra


def _regra(**overrides: object) -> Regra:
    base: dict = {
        "codigo": "TST-001",
        "nome": "Teste",
        "descricao": "Regra de teste",
        "tipo": RuleType.INTERNA,
        "categoria": "teste",
        "criticidade": RuleCriticality.ALTA,
        "acao": RuleAction.BLOQUEAR,
        "prioridade": 100,
        "vigencia": Vigencia(inicio="2026-01-01"),
        "explicacao": "Regra de teste disparada",
        "quando": GrupoCondicoes(condicoes=[
            Condicao(campo="cliente.score_bureau", operador=Operador.LT, valor=300),
        ]),
    }
    base.update(overrides)
    return Regra(**base)


def test_regra_dispara_quando_condicao_verdadeira() -> None:
    engine = RuleEngine()
    resultados = engine.avaliar(
        [_regra()], {"cliente": {"score_bureau": 250}}, produto_codigo="CRED-PESSOAL"
    )
    assert len(resultados) == 1
    assert resultados[0].disparou is True


def test_regra_nao_dispara_quando_condicao_falsa() -> None:
    engine = RuleEngine()
    resultados = engine.avaliar(
        [_regra()], {"cliente": {"score_bureau": 700}}, produto_codigo="CRED-PESSOAL"
    )
    assert resultados[0].disparou is False


def test_regra_fora_da_vigencia_nao_e_avaliada() -> None:
    engine = RuleEngine()
    regra = _regra(vigencia=Vigencia(inicio="2020-01-01", fim="2020-12-31"))
    resultados = engine.avaliar(
        [regra], {"cliente": {"score_bureau": 100}}, produto_codigo="CRED-PESSOAL"
    )
    assert resultados == []


def test_regra_de_outro_produto_nao_e_avaliada() -> None:
    engine = RuleEngine()
    regra = _regra(produto_codigo="CONSIGNADO")
    resultados = engine.avaliar(
        [regra], {"cliente": {"score_bureau": 100}}, produto_codigo="CRED-PESSOAL"
    )
    assert resultados == []


def test_grupo_or_aninhado() -> None:
    engine = RuleEngine()
    regra = _regra(quando=GrupoCondicoes(
        logica="OR",
        condicoes=[
            Condicao(campo="cliente.score_bureau", operador=Operador.LT, valor=300),
            GrupoCondicoes(logica="AND", condicoes=[
                Condicao(campo="cliente.tempo_relacionamento_meses", operador=Operador.LT, valor=6),
                Condicao(campo="proposta.prazo_meses", operador=Operador.GT, valor=48),
            ]),
        ],
    ))
    contexto = {
        "cliente": {"score_bureau": 800, "tempo_relacionamento_meses": 2},
        "proposta": {"prazo_meses": 60},
    }
    assert engine.avaliar([regra], contexto, "CRED-PESSOAL")[0].disparou is True


def test_operador_between() -> None:
    engine = RuleEngine()
    regra = _regra(quando=GrupoCondicoes(condicoes=[
        Condicao(campo="proposta.prazo_meses", operador=Operador.BETWEEN, valor=[12, 24]),
    ]))
    assert engine.avaliar([regra], {"proposta": {"prazo_meses": 18}}, "X")[0].disparou is True
    assert engine.avaliar([regra], {"proposta": {"prazo_meses": 36}}, "X")[0].disparou is False


def test_campo_ausente_gera_erro_explicito() -> None:
    engine = RuleEngine()
    with pytest.raises(RuleEngineError, match="ausente no contexto"):
        engine.avaliar([_regra()], {"cliente": {}}, "CRED-PESSOAL")
