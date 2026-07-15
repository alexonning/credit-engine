"""Modelos ORM (SQLAlchemy 2.0, tipado) das tabelas centrais."""
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class CustomerORM(Base):
    __tablename__ = "customers"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    documento: Mapped[str] = mapped_column(String(14), unique=True, index=True)
    nome: Mapped[str] = mapped_column(String(200))
    dados: Mapped[dict] = mapped_column(JSON, default=dict)  # type: ignore[type-arg]
    criado_em: Mapped[datetime] = mapped_column(default=_now)


class CreditAnalysisORM(Base):
    __tablename__ = "credit_analysis"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("customers.id"), index=True)
    produto_codigo: Mapped[str] = mapped_column(String(50), index=True)
    contexto: Mapped[dict] = mapped_column(JSON)  # type: ignore[type-arg]
    decisao: Mapped[str | None] = mapped_column(String(40), nullable=True)
    motivos: Mapped[list] = mapped_column(JSON, default=list)  # type: ignore[type-arg]
    regras_disparadas: Mapped[list] = mapped_column(JSON, default=list)  # type: ignore[type-arg]
    explicacao: Mapped[str | None] = mapped_column(Text, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(default=_now, index=True)


class RuleORM(Base):
    __tablename__ = "rules"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    codigo: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    versao_atual: Mapped[int] = mapped_column(Integer, default=1)
    ativa: Mapped[bool] = mapped_column(default=True)


class RuleVersionORM(Base):
    __tablename__ = "rule_versions"
    __table_args__ = (Index("ix_rule_versions_codigo_versao", "rule_codigo", "versao", unique=True),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    rule_codigo: Mapped[str] = mapped_column(ForeignKey("rules.codigo"))
    versao: Mapped[int] = mapped_column(Integer)
    definicao: Mapped[dict] = mapped_column(JSON)  # type: ignore[type-arg]  # Regra serializada
    criado_em: Mapped[datetime] = mapped_column(default=_now)
    criado_por: Mapped[str] = mapped_column(String(120))


class PromptVersionORM(Base):
    __tablename__ = "prompt_versions"
    __table_args__ = (Index("ix_prompt_versions_agente_versao", "agente", "versao", unique=True),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    agente: Mapped[str] = mapped_column(String(60))
    versao: Mapped[str] = mapped_column(String(20))
    system_prompt: Mapped[str] = mapped_column(Text)
    developer_prompt: Mapped[str] = mapped_column(Text)
    user_prompt_template: Mapped[str] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(default=_now)


class AgentExecutionORM(Base):
    __tablename__ = "agent_executions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    analysis_id: Mapped[UUID] = mapped_column(ForeignKey("credit_analysis.id"), index=True)
    agente: Mapped[str] = mapped_column(String(60), index=True)
    prompt_version: Mapped[str] = mapped_column(String(20))
    modelo: Mapped[str] = mapped_column(String(60))
    tokens_entrada: Mapped[int] = mapped_column(Integer, default=0)
    tokens_saida: Mapped[int] = mapped_column(Integer, default=0)
    duracao_ms: Mapped[int] = mapped_column(Integer, default=0)
    saida: Mapped[dict] = mapped_column(JSON)  # type: ignore[type-arg]
    erro: Mapped[str | None] = mapped_column(Text, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(default=_now)


class AuditLogORM(Base):
    __tablename__ = "audit_log"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    analysis_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    usuario: Mapped[str] = mapped_column(String(120), index=True)
    evento: Mapped[str] = mapped_column(String(80), index=True)
    detalhes: Mapped[dict] = mapped_column(JSON, default=dict)  # type: ignore[type-arg]
    criado_em: Mapped[datetime] = mapped_column(default=_now, index=True)
