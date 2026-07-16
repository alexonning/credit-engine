"""Classe base dos agentes especializados.

Cada agente:
  1. Avalia regras deterministicas de UMA categoria via Rule Engine.
  2. Deriva uma decisao local + score a partir dos findings.
  3. (Opcional) usa o LLM apenas para gerar o racional em linguagem natural.

O LLM nunca altera a decisao - garante auditabilidade.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.engine.rule_engine import RuleEngine
from app.llm.azure_client import LLMClient
from app.schemas.credit import AgentResult, Decision, RuleFinding, Severity


class BaseAgent(ABC):
    name: str = "base"
    category: str | None = None
    system_prompt: str = "Voce e um analista de credito. Explique de forma objetiva."

    def __init__(self, rule_engine: RuleEngine, llm: LLMClient):
        self.rule_engine = rule_engine
        self.llm = llm

    @abstractmethod
    def _score(self, ctx: dict[str, Any], findings: list[RuleFinding]) -> float: ...

    def _decision(self, findings: list[RuleFinding]) -> Decision:
        if any(not f.passed and f.severity == Severity.BLOCKER for f in findings):
            return Decision.DENIED
        if any(not f.passed and f.severity == Severity.WARNING for f in findings):
            return Decision.REVIEW
        return Decision.APPROVED

    def _rationale(self, ctx: dict[str, Any], findings: list[RuleFinding], decision: Decision) -> str:
        failed = [f for f in findings if not f.passed]
        summary = (
            f"Decisao {decision.value} do agente {self.name}. "
            f"{len(findings)} regras avaliadas, {len(failed)} nao atendidas."
        )
        if not failed:
            return summary + " Todas as regras da categoria foram atendidas."
        detail = "; ".join(f"{f.rule_id}: {f.description}" for f in failed)
        user = f"{summary}\nRegras nao atendidas: {detail}\nProduto: {ctx.get('product_code')}"
        return self.llm.complete(self.system_prompt, user)

    def run(self, ctx: dict[str, Any]) -> AgentResult:
        findings = (
            self.rule_engine.evaluate(ctx, category=self.category)
            if self.category
            else self.rule_engine.evaluate(ctx)
        )
        decision = self._decision(findings)
        score = self._score(ctx, findings)
        rationale = self._rationale(ctx, findings, decision)
        return AgentResult(
            agent=self.name,
            decision=decision,
            score=score,
            findings=findings,
            rationale=rationale,
            metadata={"category": self.category},
        )


def base_score(findings: list[RuleFinding]) -> float:
    """Score simples: proporcao de regras atendidas, penalizando blockers."""
    if not findings:
        return 1.0
    weight = {Severity.INFO: 1.0, Severity.WARNING: 2.0, Severity.BLOCKER: 4.0}
    total = sum(weight[f.severity] for f in findings)
    passed = sum(weight[f.severity] for f in findings if f.passed)
    return round(passed / total, 4) if total else 1.0
