"""Agente de Cadastro: valida a completude e consistencia dos dados cadastrais.

Nao consulta o Rule Engine de categorias de negocio; valida a integridade da
entrada (idade valida, renda positiva, documento presente). Serve de porta de
entrada antes das analises de credito propriamente ditas.
"""
from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.schemas.credit import AgentResult, Decision, RuleFinding, Severity


class CadastroAgent(BaseAgent):
    name = "cadastro"
    category = None
    system_prompt = "Voce valida dados cadastrais de credito. Seja objetivo."

    def _checks(self, ctx: dict[str, Any]) -> list[RuleFinding]:
        checks = [
            ("CAD001", "Documento informado", bool(ctx.get("document")), Severity.BLOCKER),
            ("CAD002", "Renda mensal positiva", ctx.get("monthly_income", 0) > 0, Severity.BLOCKER),
            ("CAD003", "Idade valida (>=18)", ctx.get("age", 0) >= 18, Severity.BLOCKER),
            ("CAD004", "Score de bureau presente", ctx.get("credit_score") is not None, Severity.WARNING),
        ]
        return [
            RuleFinding(
                rule_id=rid,
                category="cadastro",
                description=desc,
                passed=ok,
                severity=sev,
                detail=None if ok else f"{desc} - falhou",
            )
            for rid, desc, ok, sev in checks
        ]

    def _score(self, ctx: dict[str, Any], findings: list[RuleFinding]) -> float:
        from app.agents.base import base_score

        return base_score(findings)

    def run(self, ctx: dict[str, Any]) -> AgentResult:
        findings = self._checks(ctx)
        decision = self._decision(findings)
        score = self._score(ctx, findings)
        rationale = self._rationale(ctx, findings, decision)
        return AgentResult(
            agent=self.name,
            decision=decision,
            score=score,
            findings=findings,
            rationale=rationale,
            metadata={"category": "cadastro"},
        )
