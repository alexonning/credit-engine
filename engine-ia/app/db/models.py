"""Modelos ORM (SQLAlchemy) para persistencia e auditoria."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class CreditDecision(Base):
    __tablename__ = "credit_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(64), index=True, unique=True)
    document: Mapped[str] = mapped_column(String(32), index=True)
    product_code: Mapped[str] = mapped_column(String(32))
    decision: Mapped[str] = mapped_column(String(16))
    score: Mapped[float] = mapped_column(Numeric(6, 4))
    approved_amount: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    explanation: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(64), index=True)
    stage: Mapped[str] = mapped_column(String(48))
    decision: Mapped[str | None] = mapped_column(String(16), nullable=True)
    payload: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
