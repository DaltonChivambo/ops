"""Modelos SQLAlchemy — tradução do `schema.prisma` do MozaOps v1.

Único ponto de acesso à base de dados é `repository.py`; este módulo só
declara a forma das tabelas.

**A ordem de declaração dos enums é a ordem de leitura da tabela.** O Postgres
ordena um enum pela ordem em que os valores foram declarados no `CREATE TYPE`,
e `repository.list_details` pede `validation DESC`. Lida de baixo para cima,
`VALIDATION_VALUES` é o que o operador vê primeiro:

    duplicated · missing · mismatch · match · zero

Primeiro o que exige trabalho, depois o que confere, e no fim os zerados — que
não pedem nada a ninguém. Mexer na ordem aqui muda a tabela.

`bankaCreditsRaw` do schema original não se porta: confirmado que é escrito e
nunca lido em produção (a folha do relatório que o consumia já não existe).
"""
import uuid
from datetime import date, datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


VALIDATION_VALUES = ("zero", "match", "mismatch", "missing", "duplicated")
CLOSING_TYPE_VALUES = ("D", "D_PLUS_1", "NA")
CASE_STATUS_VALUES = ("pending", "in_review", "resolved")
CASE_TYPE_VALUES = ("missing", "mismatch")

ValidationEnum = sa.Enum(*VALIDATION_VALUES, name="validation", native_enum=True)
ClosingTypeEnum = sa.Enum(*CLOSING_TYPE_VALUES, name="closing_type", native_enum=True)
CaseStatusEnum = sa.Enum(*CASE_STATUS_VALUES, name="case_status", native_enum=True)
CaseTypeEnum = sa.Enum(*CASE_TYPE_VALUES, name="case_type", native_enum=True)

Money = sa.Numeric(18, 2)


class Execution(Base):
    __tablename__ = "execution"

    id: Mapped[str] = mapped_column(sa.String(36), primary_key=True, default=_uuid)
    executedAt: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow, index=True)
    periodStart: Mapped[date] = mapped_column(sa.Date)
    periodEnd: Mapped[date] = mapped_column(sa.Date)
    reportName: Mapped[str] = mapped_column(sa.String)
    posListFile: Mapped[str] = mapped_column(sa.String)
    simoClosingsFile: Mapped[str] = mapped_column(sa.String)
    bankaCreditsFile: Mapped[str] = mapped_column(sa.String)
    # Snapshot denormalizado do `ClosingSummary` — mutado quando um caso muda de
    # estado (ver `service._refresh_case_counters`), não só à criação.
    summary: Mapped[dict] = mapped_column(JSONB)

    details: Mapped[list["ClosingDetail"]] = relationship(
        back_populates="execution", cascade="all, delete-orphan"
    )
    cases: Mapped[list["PendingCase"]] = relationship(
        back_populates="execution", cascade="all, delete-orphan"
    )
    movements: Mapped[list["CreditMovement"]] = relationship(
        back_populates="execution", cascade="all, delete-orphan"
    )


class ClosingDetail(Base):
    """Uma linha da folha "Detalhes Validacao" — um fecho registado na SIMO."""

    __tablename__ = "closing_detail"
    __table_args__ = (
        sa.Index("ix_closing_detail_execution_validation", "executionId", "validation"),
        sa.Index("ix_closing_detail_execution_pos_id", "executionId", "posId"),
        sa.Index("ix_closing_detail_execution_key", "executionId", "key"),
    )

    id: Mapped[str] = mapped_column(sa.String(36), primary_key=True, default=_uuid)
    executionId: Mapped[str] = mapped_column(sa.ForeignKey("execution.id", ondelete="CASCADE"))
    posId: Mapped[str] = mapped_column(sa.String)
    merchant: Mapped[str] = mapped_column(sa.String)
    accountNumber: Mapped[str] = mapped_column(sa.String)
    period: Mapped[int] = mapped_column(sa.Integer)
    key: Mapped[str] = mapped_column(sa.String)
    simoClosingDate: Mapped[date] = mapped_column(sa.Date)
    operationNumber: Mapped[int] = mapped_column(sa.Integer)
    simoClosingTotal: Mapped[Decimal] = mapped_column(Money)
    # Soma SIMO da chave — o termo que a `difference` compara com `bankaClosingTotal`.
    simoKeyTotal: Mapped[Decimal] = mapped_column(Money)
    closingDescription: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    bankaCreditDate: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    bankaClosingTotal: Mapped[Decimal | None] = mapped_column(Money, nullable=True)
    closingType: Mapped[str] = mapped_column(ClosingTypeEnum)
    validation: Mapped[str] = mapped_column(ValidationEnum)
    difference: Mapped[Decimal | None] = mapped_column(Money, nullable=True)

    execution: Mapped[Execution] = relationship(back_populates="details")


class CreditMovement(Base):
    """Um movimento de crédito do Banka atribuído a uma chave — a parcela do total."""

    __tablename__ = "credit_movement"
    __table_args__ = (sa.Index("ix_credit_movement_execution_key", "executionId", "key"),)

    id: Mapped[str] = mapped_column(sa.String(36), primary_key=True, default=_uuid)
    executionId: Mapped[str] = mapped_column(sa.ForeignKey("execution.id", ondelete="CASCADE"))
    key: Mapped[str] = mapped_column(sa.String)
    movementDate: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Money)
    description: Mapped[str | None] = mapped_column(sa.String, nullable=True)

    execution: Mapped[Execution] = relationship(back_populates="movements")


class PendingCase(Base):
    """Caso de divergência para análise/regularização pelo operador."""

    __tablename__ = "pending_case"
    __table_args__ = (
        sa.UniqueConstraint("executionId", "key", name="uq_pending_case_execution_key"),
        sa.Index("ix_pending_case_execution_status", "executionId", "status"),
    )

    id: Mapped[str] = mapped_column(sa.String(36), primary_key=True, default=_uuid)
    executionId: Mapped[str] = mapped_column(sa.ForeignKey("execution.id", ondelete="CASCADE"))
    key: Mapped[str] = mapped_column(sa.String)
    posId: Mapped[str] = mapped_column(sa.String)
    period: Mapped[int] = mapped_column(sa.Integer)
    merchant: Mapped[str] = mapped_column(sa.String)
    accountNumber: Mapped[str] = mapped_column(sa.String)
    simoAmount: Mapped[Decimal] = mapped_column(Money)
    bankaAmount: Mapped[Decimal] = mapped_column(Money)
    type: Mapped[str] = mapped_column(CaseTypeEnum)
    eTicket: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    status: Mapped[str] = mapped_column(CaseStatusEnum, default="pending")
    resolvedAt: Mapped[date | None] = mapped_column(sa.Date, nullable=True)

    execution: Mapped[Execution] = relationship(back_populates="cases")
