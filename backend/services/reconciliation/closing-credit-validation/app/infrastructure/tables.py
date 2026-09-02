"""Modelos SQLAlchemy — tradução do `schema.prisma` do MozaOps v1.

Único ponto de acesso à base de dados é `repository.py`; este módulo só
declara a forma das tabelas.

**A ordem de declaração dos enums é a ordem de leitura da tabela.** O Postgres
ordena um enum pela ordem em que os valores foram declarados no `CREATE TYPE`,
e `repository.list_details` pede `validation DESC`. Lida de baixo para cima,
o `Validation` de `domain/vocabulary.py` é o que o operador vê primeiro:

    duplicated · missing · mismatch · match · zero

Primeiro o que exige trabalho, depois o que confere, e no fim os zerados — que
não pedem nada a ninguém. A ordem vive agora no vocabulário do domínio.

`bankaCreditsRaw` do schema original não se porta: confirmado que é escrito e
nunca lido em produção (a folha do relatório que o consumia já não existe).
"""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.domain.vocabulary import CaseStatus, CaseType, ClosingType, Validation


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    """Instante actual em UTC, sem fuso — a coluna `executedAt` é `DateTime` sem timezone.

    Substitui `datetime.utcnow`, depreciado no 3.12. Guarda exactamente o mesmo
    valor: pôr lá um `datetime` com fuso é que mudaria o que fica na base.
    """
    return datetime.now(UTC).replace(tzinfo=None)


def _pg_enum(enum: type[StrEnum], name: str) -> sa.Enum:
    """Enum nativo do Postgres a partir do vocabulário do domínio.

    O `values_callable` não é opcional: sem ele o SQLAlchemy persiste o NOME do
    membro (`MATCH`) e não o valor (`match`), e a coluna deixava de casar com o
    `CREATE TYPE` que já está na base.
    """
    return sa.Enum(
        enum,
        name=name,
        native_enum=True,
        values_callable=lambda membros: [membro.value for membro in membros],
    )


ValidationEnum = _pg_enum(Validation, "validation")
ClosingTypeEnum = _pg_enum(ClosingType, "closing_type")
CaseStatusEnum = _pg_enum(CaseStatus, "case_status")
CaseTypeEnum = _pg_enum(CaseType, "case_type")

Money = sa.Numeric(18, 2)


class Execution(Base):
    __tablename__ = "execution"

    id: Mapped[str] = mapped_column(sa.String(36), primary_key=True, default=_uuid)
    executedAt: Mapped[datetime] = mapped_column(sa.DateTime, default=_now, index=True)
    periodStart: Mapped[date] = mapped_column(sa.Date)
    periodEnd: Mapped[date] = mapped_column(sa.Date)
    reportName: Mapped[str] = mapped_column(sa.String)
    posListFile: Mapped[str] = mapped_column(sa.String)
    simoClosingsFile: Mapped[str] = mapped_column(sa.String)
    bankaCreditsFile: Mapped[str] = mapped_column(sa.String)
    # Snapshot denormalizado do `ClosingSummary` — mutado quando um caso muda de
    # estado (ver `service._refresh_case_counters`), não só à criação.
    summary: Mapped[dict[str, Any]] = mapped_column(JSONB)


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
    closingType: Mapped[ClosingType] = mapped_column(ClosingTypeEnum)
    validation: Mapped[Validation] = mapped_column(ValidationEnum)
    difference: Mapped[Decimal | None] = mapped_column(Money, nullable=True)


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
    type: Mapped[CaseType] = mapped_column(CaseTypeEnum)
    eTicket: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    status: Mapped[CaseStatus] = mapped_column(CaseStatusEnum, default=CaseStatus.PENDING)
    resolvedAt: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
