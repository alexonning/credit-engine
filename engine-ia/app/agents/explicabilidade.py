"""Agente de Explicabilidade: gera a explicacao final consolidada ao cliente.

Recebe a decisao final + todos os findings e produz um texto claro, em portugues,
que justifica a decisao de forma auditavel. Usa o LLM apenas para redacao; os
fatos (findings) sao imutaveis.
"""
from __future__ import annotations

from collections.abc import Iterator

from app.llm.azure_client import LLMClient
from app.schemas.credit import AgentResult, Decision, Severity

SYSTEM = (
    "Voce e um agente de explicabilidade de credito. Escreva uma justificativa "
    "clara, objetiva e em portugues do Brasil para o cliente, sem jargao tecnico "
    "excessivo. Baseie-se SOMENTE nos fatos fornecidos."
)


class ExplicabilidadeAgent:
    name = "explicabilidade"

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def _build_prompt(
        self,
        decision: Decision,
        score: float,
        results: list[AgentResult],
    ) -> tuple[str, str]:
        """Retorna (cabecalho_deterministico, prompt_do_usuario).

        O cabecalho e sempre legivel e independe da qualidade do LLM/stub;
        o prompt e o que sera enviado ao modelo para redigir a justificativa.
        """
        failed = [
            f for r in results for f in r.findings
            if not f.passed and f.severity in {Severity.BLOCKER, Severity.WARNING}
        ]
        motivos = "; ".join(f"{f.rule_id} - {f.description}" for f in failed) or "nenhum impedimento"

        user = (
            f"Decisao final: {decision.value}\n"
            f"Score consolidado: {score:.2f}\n"
            f"Fatores que pesaram: {motivos}\n"
            f"Explique ao cliente o resultado."
        )
        prefixo = {
            Decision.APPROVED: "Seu credito foi APROVADO.",
            Decision.DENIED: "Seu credito foi NEGADO.",
            Decision.REVIEW: "Seu pedido foi encaminhado para ANALISE / NEGOCIACAO.",
        }[decision]
        header = f"{prefixo} (score {score:.2f}). Fatores: {motivos}. "
        return header, user

    def explain(
        self,
        decision: Decision,
        score: float,
        results: list[AgentResult],
    ) -> str:
        header, user = self._build_prompt(decision, score, results)
        text = self.llm.complete(SYSTEM, user)
        return header + text

    def explain_stream(
        self,
        decision: Decision,
        score: float,
        results: list[AgentResult],
    ) -> Iterator[str]:
        """Versao streaming: emite o cabecalho na hora e depois os tokens do LLM."""
        header, user = self._build_prompt(decision, score, results)
        yield header
        yield from self.llm.stream(SYSTEM, user)
