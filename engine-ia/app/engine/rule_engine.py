"""Rule Engine deterministico, totalmente desacoplado do LLM.

As regras sao declaradas em YAML e avaliadas contra um "contexto" plano
(dicionario de variaveis derivadas do CreditRequest). A avaliacao NAO depende
de nenhum modelo de linguagem - garante reprodutibilidade e auditabilidade.

Cada regra tem o formato:

    - id: SIS001
      description: "Score minimo sistemico"
      severity: BLOCKER          # INFO | WARNING | BLOCKER
      when: "credit_score < 300"  # opcional: so aplica a regra se verdadeiro
      expr: "credit_score >= 300" # condicao que precisa ser verdadeira para PASSAR
"""
from __future__ import annotations

import ast
import operator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from app.schemas.credit import RuleFinding, Severity

# --- Mini avaliador de expressoes seguro (sem eval do Python) ---------------

_ALLOWED_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_ALLOWED_CMP = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
}
_ALLOWED_BOOL = {ast.And: all, ast.Or: any}


class RuleEvalError(Exception):
    """Erro ao avaliar expressao de regra."""


def _eval_node(node: ast.AST, ctx: dict[str, Any]) -> Any:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, ctx)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id in ctx:
            return ctx[node.id]
        raise RuleEvalError(f"variavel desconhecida: {node.id}")
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return not _eval_node(node.operand, ctx)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval_node(node.operand, ctx)
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINOPS:
        return _ALLOWED_BINOPS[type(node.op)](
            _eval_node(node.left, ctx), _eval_node(node.right, ctx)
        )
    if isinstance(node, ast.BoolOp) and type(node.op) in _ALLOWED_BOOL:
        values = [_eval_node(v, ctx) for v in node.values]
        return _ALLOWED_BOOL[type(node.op)](values)
    if isinstance(node, ast.Compare):
        left = _eval_node(node.left, ctx)
        for op, comparator in zip(node.ops, node.comparators):
            right = _eval_node(comparator, ctx)
            if type(op) not in _ALLOWED_CMP:
                raise RuleEvalError(f"operador nao permitido: {type(op).__name__}")
            if not _ALLOWED_CMP[type(op)](left, right):
                return False
            left = right
        return True
    raise RuleEvalError(f"expressao nao suportada: {ast.dump(node)}")


def safe_eval(expr: str, ctx: dict[str, Any]) -> Any:
    try:
        tree = ast.parse(expr, mode="eval")
        return _eval_node(tree, ctx)
    except RuleEvalError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise RuleEvalError(f"falha ao avaliar '{expr}': {exc}") from exc


# --- Modelo de regra --------------------------------------------------------

@dataclass(frozen=True)
class Rule:
    id: str
    category: str
    description: str
    expr: str
    severity: Severity = Severity.INFO
    when: str | None = None
    product_scope: list[str] | None = None  # aplica so a estes produtos

    def applies_to(self, ctx: dict[str, Any]) -> bool:
        if self.product_scope:
            if ctx.get("product_code") not in self.product_scope:
                return False
        if self.when:
            return bool(safe_eval(self.when, ctx))
        return True

    def evaluate(self, ctx: dict[str, Any]) -> RuleFinding:
        passed = bool(safe_eval(self.expr, ctx))
        return RuleFinding(
            rule_id=self.id,
            category=self.category,
            description=self.description,
            passed=passed,
            severity=self.severity,
            detail=None if passed else f"Regra '{self.id}' nao atendida: {self.expr}",
        )


class RuleEngine:
    """Carrega regras de arquivos YAML e as avalia por categoria."""

    def __init__(self, rules: list[Rule]):
        self._rules = rules

    @classmethod
    def from_dir(cls, rules_dir: str | Path) -> "RuleEngine":
        rules_dir = Path(rules_dir)
        rules: list[Rule] = []
        for path in sorted(rules_dir.glob("*.yaml")):
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            category = data.get("category", path.stem)
            for raw in data.get("rules", []):
                rules.append(
                    Rule(
                        id=raw["id"],
                        category=category,
                        description=raw.get("description", ""),
                        expr=raw["expr"],
                        severity=Severity(raw.get("severity", "INFO")),
                        when=raw.get("when"),
                        product_scope=raw.get("product_scope"),
                    )
                )
        return cls(rules)

    def evaluate(self, ctx: dict[str, Any], category: str | None = None) -> list[RuleFinding]:
        findings: list[RuleFinding] = []
        for rule in self._rules:
            if category and rule.category != category:
                continue
            if not rule.applies_to(ctx):
                continue
            findings.append(rule.evaluate(ctx))
        return findings

    @property
    def rules(self) -> list[Rule]:
        return list(self._rules)
