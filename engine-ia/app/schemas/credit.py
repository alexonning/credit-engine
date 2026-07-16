"""Modelos Pydantic de entrada e saida da analise de credito."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Decision(str, Enum):
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    REVIEW = "REVIEW"  # analise manual / negociacao


class Severity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    BLOCKER = "BLOCKER"  # reprova automaticamente


# ---------- Entrada ----------

class Applicant(BaseModel):
    """Dados cadastrais do solicitante."""
    document: str = Field(..., description="CPF/CNPJ")
    name: str
    birth_date: datetime | None = None
    monthly_income: Decimal = Field(..., ge=0)
    existing_debt: Decimal = Field(default=Decimal("0"), ge=0)
    credit_score: int = Field(..., ge=0, le=1000)
    employment_status: str = Field(default="employed")
    region: str | None = None
    is_blacklisted: bool = False


class ProductRequest(BaseModel):
    """Produto de credito solicitado."""
    product_code: str = Field(..., description="Ex.: CDC, CONSIGNADO, CARTAO, HOME_EQUITY")
    amount: Decimal = Field(..., gt=0)
    term_months: int = Field(..., gt=0, le=480)


class CreditRequest(BaseModel):
    applicant: Applicant
    product: ProductRequest
    channel: str = Field(default="api")
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------- Saida ----------

class RuleFinding(BaseModel):
    """Resultado de UMA regra avaliada pelo rule engine."""
    rule_id: str
    category: str  # sistemica | interna | concessao | produto
    description: str
    passed: bool
    severity: Severity = Severity.INFO
    detail: str | None = None


class AgentResult(BaseModel):
    """Saida padronizada de um agente especializado."""
    agent: str
    decision: Decision
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    findings: list[RuleFinding] = Field(default_factory=list)
    rationale: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class NegotiationOffer(BaseModel):
    approved_amount: Decimal
    term_months: int
    interest_rate: float
    conditions: list[str] = Field(default_factory=list)


class CreditResponse(BaseModel):
    request_id: str
    decision: Decision
    score: float
    approved_amount: Decimal | None = None
    agent_results: list[AgentResult] = Field(default_factory=list)
    offer: NegotiationOffer | None = None
    explanation: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
