"""Modelos SQLAlchemy — tradução do `schema.prisma` do MozaOps v1."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.domain.sla import DEFAULT_SLA_DAYS, DEFAULT_WARNING_DAYS
from app.domain.vocabulary import CaseDateSource, CaseStatus, CaseType, ClosingType, Validation


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    """Instante actual em UTC, sem fuso — a coluna `executedAt` é `DateTime` sem timezone."""
    return datetime.now(UTC).replace(tzinfo=None)


def _pg_enum(enum: type[StrEnum], name: str) -> sa.Enum:
    """Enum nativo do Postgres a partir do vocabulário do domínio."""
    return sa.Enum(
        enum,
        name=name,
        native_enum=True,
        values_callable=lambda members: [member.value for member in members],
    )


ValidationEnum = _pg_enum(Validation, "validation")
ClosingTypeEnum = _pg_enum(ClosingType, "closing_type")
CaseStatusEnum = _pg_enum(CaseStatus, "case_status")
CaseTypeEnum = _pg_enum(CaseType, "case_type")
CaseDateSourceEnum = _pg_enum(CaseDateSource, "case_date_source")

Money = sa.Numeric(18, 2)


class Execution(Base):
    __tablename__ = "execution"

    id: Mapped[str] = mapped_column(sa.String(36), primary_key=True, default=_uuid)
    executed_at: Mapped[datetime] = mapped_column(
        "executedAt", sa.DateTime, default=_now, index=True
    )
    period_start: Mapped[date] = mapped_column("periodStart", sa.Date)
    period_end: Mapped[date] = mapped_column("periodEnd", sa.Date)
    report_name: Mapped[str] = mapped_column("reportName", sa.String)
    pos_list_file: Mapped[str] = mapped_column("posListFile", sa.String)
    simo_closings_file: Mapped[str] = mapped_column("simoClosingsFile", sa.String)
    banka_credits_file: Mapped[str] = mapped_column("bankaCreditsFile", sa.String)
    # Snapshot do `ClosingSummary`, reescrito a cada mudança de caso.
    summary: Mapped[dict[str, Any]] = mapped_column(JSONB)
    # Contar os repetidos do export como fechos: decisão da execução, igual para todos.
    count_simo_duplicates: Mapped[bool] = mapped_column(
        "countSimoDuplicates", sa.Boolean, default=False, server_default=sa.false()
    )


class ClosingDetail(Base):
    """Uma linha da folha "Detalhes Validacao" — um fecho registado na SIMO."""

    __tablename__ = "closing_detail"
    __table_args__ = (
        sa.Index("ix_closing_detail_execution_validation", "executionId", "validation"),
        sa.Index("ix_closing_detail_execution_pos_id", "executionId", "posId"),
        sa.Index("ix_closing_detail_execution_key", "executionId", "key"),
        # A ordem da tabela inteira, num índice: sem ela cada página ordenava tudo.
        sa.Index(
            "ix_closing_detail_reading_order",
            "executionId",
            "sortRank",
            "posId",
            "period",
            "simoClosingDate",
            "simoDuplicate",
            "operationNumber",
        ),
    )

    id: Mapped[str] = mapped_column(sa.String(36), primary_key=True, default=_uuid)
    execution_id: Mapped[str] = mapped_column(
        "executionId", sa.ForeignKey("execution.id", ondelete="CASCADE")
    )
    pos_id: Mapped[str] = mapped_column("posId", sa.String)
    merchant: Mapped[str] = mapped_column(sa.String)
    account_number: Mapped[str] = mapped_column("accountNumber", sa.String)
    period: Mapped[int] = mapped_column(sa.Integer)
    key: Mapped[str] = mapped_column(sa.String)
    simo_closing_date: Mapped[date] = mapped_column("simoClosingDate", sa.Date)
    operation_number: Mapped[int] = mapped_column("operationNumber", sa.Integer)
    simo_closing_total: Mapped[Decimal] = mapped_column("simoClosingTotal", Money)
    # Soma SIMO da chave — o termo que a `difference` compara com `bankaClosingTotal`.
    simo_key_total: Mapped[Decimal] = mapped_column("simoKeyTotal", Money)
    closing_description: Mapped[str | None] = mapped_column(
        "closingDescription", sa.String, nullable=True
    )
    banka_credit_date: Mapped[date | None] = mapped_column(
        "bankaCreditDate", sa.Date, nullable=True
    )
    banka_closing_total: Mapped[Decimal | None] = mapped_column(
        "bankaClosingTotal", Money, nullable=True
    )
    closing_type: Mapped[ClosingType] = mapped_column("closingType", ClosingTypeEnum)
    validation: Mapped[Validation] = mapped_column(ValidationEnum)
    difference: Mapped[Decimal | None] = mapped_column(Money, nullable=True)
    # Linha duplicada no export: conta e fica marcada.
    simo_duplicate: Mapped[bool] = mapped_column(
        "simoDuplicate", sa.Boolean, default=False, server_default=sa.false()
    )
    has_simo_duplicate: Mapped[bool] = mapped_column(
        "hasSimoDuplicate", sa.Boolean, default=False, server_default=sa.false()
    )
    #: A ordem de leitura do operador, materializada — ver `execution_repository`.
    sort_rank: Mapped[int] = mapped_column("sortRank", sa.SmallInteger)


class CreditMovement(Base):
    """Um movimento de crédito do Banka atribuído a uma chave — a parcela do total."""

    __tablename__ = "credit_movement"
    __table_args__ = (sa.Index("ix_credit_movement_execution_key", "executionId", "key"),)

    id: Mapped[str] = mapped_column(sa.String(36), primary_key=True, default=_uuid)
    execution_id: Mapped[str] = mapped_column(
        "executionId", sa.ForeignKey("execution.id", ondelete="CASCADE")
    )
    key: Mapped[str] = mapped_column(sa.String)
    movement_date: Mapped[date | None] = mapped_column("movementDate", sa.Date, nullable=True)
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
    execution_id: Mapped[str] = mapped_column(
        "executionId", sa.ForeignKey("execution.id", ondelete="CASCADE")
    )
    key: Mapped[str] = mapped_column(sa.String)
    pos_id: Mapped[str] = mapped_column("posId", sa.String)
    period: Mapped[int] = mapped_column(sa.Integer)
    merchant: Mapped[str] = mapped_column(sa.String)
    account_number: Mapped[str] = mapped_column("accountNumber", sa.String)
    simo_amount: Mapped[Decimal] = mapped_column("simoAmount", Money)
    banka_amount: Mapped[Decimal] = mapped_column("bankaAmount", Money)
    type: Mapped[CaseType] = mapped_column(CaseTypeEnum)
    # A primeira data da chave e de que lado veio; daqui conta o prazo.
    first_date: Mapped[date] = mapped_column("firstDate", sa.Date)
    first_date_source: Mapped[CaseDateSource] = mapped_column("firstDateSource", CaseDateSourceEnum)
    e_ticket: Mapped[str | None] = mapped_column("eTicket", sa.String, nullable=True)
    status: Mapped[CaseStatus] = mapped_column(CaseStatusEnum, default=CaseStatus.PENDING)
    # Desde quando está neste estado; muda a cada mudança, ao contrário do `resolvedAt`.
    status_since: Mapped[date] = mapped_column("statusSince", sa.Date, default=date.today)
    resolved_at: Mapped[date | None] = mapped_column("resolvedAt", sa.Date, nullable=True)


class ClosingMatch(Base):
    """Um fecho da SIMO conciliado com um movimento do Banka, numa chave duplicada."""

    __tablename__ = "closing_match"
    __table_args__ = (sa.Index("ix_closing_match_execution_key", "executionId", "key"),)

    id: Mapped[str] = mapped_column(sa.String(36), primary_key=True, default=_uuid)
    execution_id: Mapped[str] = mapped_column(
        "executionId", sa.ForeignKey("execution.id", ondelete="CASCADE")
    )
    key: Mapped[str] = mapped_column(sa.String)
    closing_id: Mapped[str] = mapped_column(
        "closingId", sa.ForeignKey("closing_detail.id", ondelete="CASCADE"), unique=True
    )
    movement_id: Mapped[str] = mapped_column(
        "movementId", sa.ForeignKey("credit_movement.id", ondelete="CASCADE"), unique=True
    )
    # Quem declarou que este crédito pagou este fecho, e quando.
    matched_at: Mapped[datetime] = mapped_column("matchedAt", sa.DateTime, default=_now)
    matched_by: Mapped[str | None] = mapped_column("matchedBy", sa.String, nullable=True)


class Setting(Base):
    """As definições do serviço — uma linha só, sempre a de `id = 1`."""

    __tablename__ = "setting"
    __table_args__ = (sa.CheckConstraint("id = 1", name="ck_setting_single_row"),)

    id: Mapped[int] = mapped_column(sa.SmallInteger, primary_key=True, default=1)
    case_sla_days: Mapped[int] = mapped_column(
        "caseSlaDays", sa.Integer, server_default=str(DEFAULT_SLA_DAYS)
    )
    case_warning_days: Mapped[int] = mapped_column(
        "caseWarningDays", sa.Integer, server_default=str(DEFAULT_WARNING_DAYS)
    )
    updated_at: Mapped[datetime] = mapped_column("updatedAt", sa.DateTime, default=_now)
    updated_by: Mapped[str | None] = mapped_column("updatedBy", sa.String, nullable=True)
