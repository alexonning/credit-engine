"""Entidades e agregados do domínio."""
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.domain.enums import DecisionOutcome
from app.domain.value_objects import Dinheiro, Documento, Score


class Cliente(BaseModel):
    """Entidade Cliente (cooperado)."""
    id: UUID = Field(default_factory=uuid4)
    documento: Documento
    nome: str
    renda_mensal: Dinheiro
    tempo_relacionamento_meses: int = 0
    scores: list[Score] = Field(default_factory=list)

    @property
    def melhor_score(self) -> int:
        return max((s.valor for s in self.scores), default=0)


class PropostaCredito(BaseModel):
    """Proposta solicitada pelo cliente."""
    produto_codigo: str
    valor_solicitado: Dinheiro
    prazo_meses: int
    finalidade: str | None = None

    @property
    def parcela_estimada(self) -> Decimal:
        """Parcela linear simples usada apenas como referência de comprometimento.

        O cálculo financeiro real (Price/SAC com taxa do produto) é feito
        pelo ProdutoAgent com os parâmetros vigentes do produto.
        """
        return (self.valor_solicitado.valor / self.prazo_meses).quantize(Decimal("0.01"))


class AnaliseCredito(BaseModel):
    """Aggregate root da análise de crédito."""
    id: UUID = Field(default_factory=uuid4)
    cliente: Cliente
    proposta: PropostaCredito
    criado_em: datetime = Field(default_factory=lambda: datetime.now(UTC))
    decisao: DecisionOutcome | None = None
    motivos: list[str] = Field(default_factory=list)
    restricoes: list[str] = Field(default_factory=list)
    documentos_pendentes: list[str] = Field(default_factory=list)
    garantias_exigidas: list[str] = Field(default_factory=list)
