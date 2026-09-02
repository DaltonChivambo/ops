"""O contrato REST, tipado — espelha `data/models.ts` do SPA, campo a campo.

Substitui os `*_to_dict` escritos à mão. O ganho não é estética: o contrato
deixa de viver em funções soltas que ninguém verifica e passa a ser uma
declaração que gera OpenAPI e que o `test_contract.py` confere contra o
`models.ts`.

**As chaves são o contrato e não mudam.** Os `Decimal` saem como número (o SPA
formata com `Intl`), as datas em ISO, e dois enums são traduzidos porque o
frontend sempre os leu assim: `D_PLUS_1` → `D+1`, `NA` → `n.a`, `in_review` →
`in-review`.
"""

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from app.domain.vocabulary import CaseStatus, CaseType, ClosingType, Validation
from app.infrastructure.tables import ClosingDetail, CreditMovement, Execution, PendingCase

ClosingTypeLabel = Literal["D", "D+1", "n.a"]
CaseStatusLabel = Literal["pending", "in-review", "resolved"]

CLOSING_TYPE_LABELS: dict[ClosingType, ClosingTypeLabel] = {
    ClosingType.D: "D",
    ClosingType.D_PLUS_1: "D+1",
    ClosingType.NA: "n.a",
}
CASE_STATUS_LABELS: dict[CaseStatus, CaseStatusLabel] = {
    CaseStatus.PENDING: "pending",
    CaseStatus.IN_REVIEW: "in-review",
    CaseStatus.RESOLVED: "resolved",
}


class Schema(BaseModel):
    """Base de todos: proíbe campos a mais, que numa resposta é sempre engano."""

    model_config = ConfigDict(extra="forbid")


# ─── Saída ───────────────────────────────────────────────────────────────────


class ClosingDetailOut(Schema):
    """Uma linha da folha «Detalhes Validacao» — um fecho registado na SIMO."""

    id: str
    posId: str
    merchant: str
    accountNumber: str
    period: int
    key: str
    simoClosingDate: date
    operationNumber: int
    simoClosingTotal: float
    simoKeyTotal: float
    closingDescription: str | None
    bankaCreditDate: date | None
    bankaClosingTotal: float | None
    closingType: ClosingTypeLabel
    validation: Validation
    difference: float | None

    @classmethod
    def from_row(cls, row: ClosingDetail) -> "ClosingDetailOut":
        return cls(
            id=row.id,
            posId=row.posId,
            merchant=row.merchant,
            accountNumber=row.accountNumber,
            period=row.period,
            key=row.key,
            simoClosingDate=row.simoClosingDate,
            operationNumber=row.operationNumber,
            simoClosingTotal=float(row.simoClosingTotal),
            simoKeyTotal=float(row.simoKeyTotal),
            closingDescription=row.closingDescription,
            bankaCreditDate=row.bankaCreditDate,
            bankaClosingTotal=(
                float(row.bankaClosingTotal) if row.bankaClosingTotal is not None else None
            ),
            closingType=CLOSING_TYPE_LABELS[row.closingType],
            validation=row.validation,
            difference=float(row.difference) if row.difference is not None else None,
        )


class CreditMovementOut(Schema):
    """Um movimento de crédito do Banka atribuído a uma chave — a parcela do total."""

    id: str
    key: str
    date: date | None
    amount: float
    description: str | None

    @classmethod
    def from_row(cls, row: CreditMovement) -> "CreditMovementOut":
        return cls(
            id=row.id,
            key=row.key,
            date=row.movementDate,
            amount=float(row.amount),
            description=row.description,
        )


class PendingCaseOut(Schema):
    """Caso de divergência para análise/regularização pelo operador."""

    id: str
    key: str
    posId: str
    period: int
    merchant: str
    accountNumber: str
    simoAmount: float
    bankaAmount: float
    type: CaseType
    eTicket: str | None
    status: CaseStatusLabel
    resolvedAt: date | None

    @classmethod
    def from_row(cls, row: PendingCase) -> "PendingCaseOut":
        return cls(
            id=row.id,
            key=row.key,
            posId=row.posId,
            period=row.period,
            merchant=row.merchant,
            accountNumber=row.accountNumber,
            simoAmount=float(row.simoAmount),
            bankaAmount=float(row.bankaAmount),
            type=row.type,
            eTicket=row.eTicket,
            status=CASE_STATUS_LABELS[row.status],
            resolvedAt=row.resolvedAt,
        )


class ExecutionFilesOut(Schema):
    """Os nomes dos três ficheiros que deram origem à execução."""

    posList: str
    simoClosings: str
    bankaCredits: str


class ValidationResultOut(Schema):
    """Uma execução persistida. Os detalhes vêm à parte, paginados."""

    executionId: str
    executedAt: datetime
    periodStart: date
    periodEnd: date
    reportName: str
    files: ExecutionFilesOut
    # Não é tipado campo a campo de propósito: é o documento JSONB tal como foi
    # gravado, e o `ClosingSummary` do domínio é que manda na sua forma. Tipá-lo
    # aqui obrigava a manter duas listas de 21 campos em dia uma com a outra.
    summary: dict[str, Any]
    cases: list[PendingCaseOut]

    @classmethod
    def from_row(cls, row: Execution, cases: list[PendingCase]) -> "ValidationResultOut":
        return cls(
            executionId=row.id,
            executedAt=row.executedAt,
            periodStart=row.periodStart,
            periodEnd=row.periodEnd,
            reportName=row.reportName,
            files=ExecutionFilesOut(
                posList=row.posListFile,
                simoClosings=row.simoClosingsFile,
                bankaCredits=row.bankaCreditsFile,
            ),
            summary=row.summary,
            cases=[PendingCaseOut.from_row(case) for case in cases],
        )


class KeyBreakdownOut(Schema):
    """Os dois lados de uma chave — o que o painel de detalhe de um fecho mostra."""

    key: str
    closings: list[ClosingDetailOut]
    movements: list[CreditMovementOut]
    case: PendingCaseOut | None

    @classmethod
    def from_parts(
        cls,
        key: str,
        closings: list[ClosingDetail],
        movements: list[CreditMovement],
        case: PendingCase | None,
    ) -> "KeyBreakdownOut":
        return cls(
            key=key,
            closings=[ClosingDetailOut.from_row(row) for row in closings],
            movements=[CreditMovementOut.from_row(row) for row in movements],
            case=PendingCaseOut.from_row(case) if case else None,
        )


class DetailCountsOut(Schema):
    """Contagens dos chips — sobre toda a execução, não sobre a página."""

    all: int
    match: int
    mismatch: int
    missing: int
    zero: int
    duplicated: int


class DetailsPageOut(Schema):
    """Página da tabela de reconciliação — filtrada e contada no servidor."""

    items: list[ClosingDetailOut]
    total: int
    page: int
    perPage: int
    counts: DetailCountsOut


class CaseUpdateOut(Schema):
    """O caso como ficou, e o `summary` da execução já recalculado."""

    case: PendingCaseOut
    summary: dict[str, Any]


# ─── Entrada ─────────────────────────────────────────────────────────────────


class CasePatchIn(BaseModel):
    """O que o operador pode mudar num caso. Ambos opcionais: manda-se só um.

    O `status` fica `str` e não `Literal` de propósito — quem sabe que estados
    existem e como se passa de um para o outro é o domínio, e é ele que devolve
    a mensagem em português quando o valor não serve. Validá-lo aqui trocava
    essa mensagem por uma do Pydantic.
    """

    model_config = ConfigDict(extra="ignore")

    status: str | None = None
    eTicket: str | None = None
