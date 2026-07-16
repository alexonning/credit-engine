"""Testes do Rule Engine deterministico e do avaliador seguro de expressoes."""
from __future__ import annotations

import pytest

from app.config import settings
from app.engine.rule_engine import RuleEngine, RuleEvalError, safe_eval


def test_safe_eval_arithmetic_and_comparison():
    assert safe_eval("a >= 300", {"a": 500}) is True
    assert safe_eval("a * 10 >= b", {"a": 100, "b": 500}) is True
    assert safe_eval("x == 'CDC'", {"x": "CDC"}) is True
    assert safe_eval("a > 1 and b < 2", {"a": 5, "b": 1}) is True


def test_safe_eval_blocks_unknown_variable():
    with pytest.raises(RuleEvalError):
        safe_eval("desconhecida > 1", {})


def test_safe_eval_blocks_arbitrary_code():
    # nao deve permitir chamadas de funcao / acesso a atributos
    with pytest.raises(RuleEvalError):
        safe_eval("__import__('os').system('echo x')", {})


def test_rule_engine_loads_and_evaluates():
    engine = RuleEngine.from_dir(settings.rules_dir)
    assert len(engine.rules) > 0

    ctx = {
        "credit_score": 720,
        "is_blacklisted": False,
        "age": 30,
        "dti": 0.2,
        "monthly_income": 6000,
        "amount": 20000,
        "term_months": 24,
        "estimated_installment": 1000,
        "employment_status": "employed",
        "product_code": "CDC",
    }
    sistemicas = engine.evaluate(ctx, category="sistemica")
    assert all(f.passed for f in sistemicas)


def test_product_scope_filters_rules():
    engine = RuleEngine.from_dir(settings.rules_dir)
    ctx = {
        "product_code": "CONSIGNADO",
        "employment_status": "unemployed",
        "term_months": 100,
        "amount": 10000,
        "monthly_income": 6000,
    }
    produto = engine.evaluate(ctx, category="produto")
    ids = {f.rule_id for f in produto}
    # regras de consignado aplicam; regras de CDC nao
    assert "PRD_CON_001" in ids
    assert "PRD_CDC_001" not in ids
