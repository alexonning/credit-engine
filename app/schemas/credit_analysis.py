"""Schemas da API (Presentation Layer)."""
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.enums import DecisionOutcome


class ClienteRequest(BaseModel):
    documento: str
    nome: str
    renda_mensal: Decimal = Field(gt=0)
    ocupacao: str
    endereco: str
    telefone: str
    tempo_relacionamento_meses: int = Field(ge=0)
    score_bureau: int = Field(ge=0, le=1000)


class PropostaRequest(BaseModel):
    produto_codigo: str
    valor_solicitado: Decimal = Field(gt=0)
    prazo_meses: int = Field(gt=0, le=360)
    finalidade: str | None = None


class AnaliseCreditoRequest(BaseModel):
    cliente: ClienteRequest
    proposta: PropostaRequest


class AnaliseCreditoResponse(BaseModel):
    analysis_id: UUID
    decisao: DecisionOutcome
    motivos: list[str]
    restricoes: list[str]
    documentos_pendentes: list[str]
    garantias_exigidas: list[str]
    regras_disparadas: list[str]
    permite_contraproposta: bool
    explicacao: str
