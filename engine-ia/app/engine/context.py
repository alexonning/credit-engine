"""Constroi o contexto plano de variaveis usado pelo Rule Engine.

Traduz o CreditRequest (aninhado, tipado) para um dicionario simples de numeros
e strings que as expressoes das regras conseguem referenciar diretamente.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from app.schemas.credit import CreditRequest


def _age_from_birth(birth: datetime | None) -> int:
    if birth is None:
        return 30  # default neutro quando nao informado
    today = datetime.utcnow()
    years = today.year - birth.year
    if (today.month, today.day) < (birth.month, birth.day):
        years -= 1
    return years


def estimate_installment(amount: Decimal, term_months: int, annual_rate: float = 0.24) -> float:
    """Estima a parcela usando o sistema Price (juros compostos)."""
    monthly_rate = annual_rate / 12
    n = term_months
    p = float(amount)
    if monthly_rate == 0:
        return p / n
    factor = (monthly_rate * (1 + monthly_rate) ** n) / ((1 + monthly_rate) ** n - 1)
    return round(p * factor, 2)


def build_context(request: CreditRequest) -> dict[str, Any]:
    app_ = request.applicant
    prod = request.product

    income = float(app_.monthly_income)
    debt = float(app_.existing_debt)
    installment = estimate_installment(prod.amount, prod.term_months)

    # DTI (Debt-to-Income): comprometimento de renda incluindo a nova parcela.
    dti = (debt + installment) / income if income > 0 else 1.0

    return {
        # cadastro
        "document": app_.document,
        "age": _age_from_birth(app_.birth_date),
        "monthly_income": income,
        "existing_debt": debt,
        "credit_score": app_.credit_score,
        "employment_status": app_.employment_status,
        "is_blacklisted": app_.is_blacklisted,
        "region": app_.region or "NA",
        # produto
        "product_code": prod.product_code,
        "amount": float(prod.amount),
        "term_months": prod.term_months,
        # derivados
        "estimated_installment": installment,
        "dti": round(dti, 4),
    }
