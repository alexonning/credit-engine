"""Fixtures compartilhadas dos testes."""
from __future__ import annotations

import os
from decimal import Decimal

import pytest

# Garante modo stub (sem chamadas externas) durante os testes.
os.environ.setdefault("LLM_USE_STUB", "true")

from app.schemas.credit import Applicant, CreditRequest, ProductRequest  # noqa: E402


@pytest.fixture
def good_request() -> CreditRequest:
    return CreditRequest(
        applicant=Applicant(
            document="12345678900",
            name="Maria Silva",
            monthly_income=Decimal("6000"),
            existing_debt=Decimal("300"),
            credit_score=720,
            employment_status="employed",
        ),
        product=ProductRequest(product_code="CDC", amount=Decimal("20000"), term_months=24),
    )


@pytest.fixture
def blacklisted_request() -> CreditRequest:
    return CreditRequest(
        applicant=Applicant(
            document="99999999999",
            name="Joao Restrito",
            monthly_income=Decimal("6000"),
            credit_score=720,
            is_blacklisted=True,
        ),
        product=ProductRequest(product_code="CDC", amount=Decimal("10000"), term_months=24),
    )
