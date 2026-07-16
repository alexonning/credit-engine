"""Testes do Decision Engine (consolidacao deterministica)."""
from __future__ import annotations

from decimal import Decimal

from app.engine.decision_engine import approved_amount, consolidate
from app.schemas.credit import AgentResult, Decision, RuleFinding, Severity


def _finding(passed: bool, severity: Severity) -> RuleFinding:
    return RuleFinding(
        rule_id="X", category="c", description="d", passed=passed, severity=severity
    )


def test_blocker_causes_denied():
    results = [
        AgentResult(agent="regras_sistemicas", decision=Decision.DENIED, score=0.2,
                    findings=[_finding(False, Severity.BLOCKER)]),
    ]
    decision, _ = consolidate(results)
    assert decision == Decision.DENIED


def test_warning_causes_review():
    results = [
        AgentResult(agent="regras_internas", decision=Decision.REVIEW, score=0.6,
                    findings=[_finding(False, Severity.WARNING)]),
    ]
    decision, _ = consolidate(results)
    assert decision == Decision.REVIEW


def test_all_pass_approved():
    results = [
        AgentResult(agent="concessao", decision=Decision.APPROVED, score=1.0,
                    findings=[_finding(True, Severity.INFO)]),
    ]
    decision, score = consolidate(results)
    assert decision == Decision.APPROVED
    assert score > 0


def test_approved_amount_partial_on_review():
    amount = approved_amount(Decimal("10000"), Decision.REVIEW, 0.6)
    assert amount is not None
    assert Decimal("4000") <= amount <= Decimal("9000")


def test_approved_amount_none_on_denied():
    assert approved_amount(Decimal("10000"), Decision.DENIED, 0.9) is None
