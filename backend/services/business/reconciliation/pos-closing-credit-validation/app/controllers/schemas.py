"""O contrato REST, tipado — espelha `data/models.ts` do SPA, campo a campo."""

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.domain.matching import Match
from app.domain.vocabulary import (
    CaseDateSource,
    CaseStatus,
    CaseType,
    ClosingType,
    Validation,
)
from app.infrastructure.tables import (
    ClosingDetail,
    ClosingMatch,
    CreditMovement,
    Execution,
    PendingCase,
)
from app.services.settings_service import SlaSettings

ClosingTypeLabel = Literal["D", "D+1", "n.a"]
CaseStatusLabel = Literal["pending", "in-review-internal", "in-review-simo", "resolved"]

CLOSING_TYPE_LABELS: dict[ClosingType, ClosingTypeLabel] = {
    ClosingType.D: "D",
    ClosingType.D_PLUS_1: "D+1",
    ClosingType.NA: "n.a",
}
CASE_STATUS_LABELS: dict[CaseStatus, CaseStatusLabel] = {
    CaseStatus.PENDING: "pending",
    CaseStatus.IN_REVIEW_INTERNAL: "in-review-internal",
    CaseStatus.IN_REVIEW_SIMO: "in-review-simo",
    CaseStatus.RESOLVED: "resolved",
}


class Schema(BaseModel):
    """Base de todos os modelos de saída."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


# ─── Saída ───────────────────────────────────────────────────────────────────


class ClosingDetailOut(Schema):
    """Uma linha da folha «Detalhes Validacao» — um fecho registado na SIMO."""

    id: str
    pos_id: str
    merchant: str
    account_number: str
    period: int
    key: str
    simo_closing_date: date
    operation_number: int
    simo_closing_total: float
    simo_key_total: float
    closing_description: str | None
    banka_credit_date: date | None
    banka_closing_total: float | None
    closing_type: ClosingTypeLabel
    validation: Validation
    difference: float | None
    # Contagens da chave: não são colunas persistidas, vêm à parte (`count_by_key`).
    # `has_simo_duplicate` é a outra ponta do par: o original que tem cópias.
    simo_duplicate: bool
    has_simo_duplicate: bool
    simo_closings_count: int
    banka_movements_count: int

    @classmethod
    def from_row(
        cls,
        row: ClosingDetail,
        simo_closings_count: int = 1,
        banka_movements_count: int = 1,
    ) -> ClosingDetailOut:
        return cls(
            id=row.id,
            pos_id=row.pos_id,
            merchant=row.merchant,
            account_number=row.account_number,
            period=row.period,
            key=row.key,
            simo_closing_date=row.simo_closing_date,
            operation_number=row.operation_number,
            simo_closing_total=float(row.simo_closing_total),
            simo_key_total=float(row.simo_key_total),
            closing_description=row.closing_description,
            banka_credit_date=row.banka_credit_date,
            banka_closing_total=(
                float(row.banka_closing_total) if row.banka_closing_total is not None else None
            ),
            closing_type=CLOSING_TYPE_LABELS[row.closing_type],
            validation=row.validation,
            difference=float(row.difference) if row.difference is not None else None,
            simo_duplicate=bool(row.simo_duplicate),
            has_simo_duplicate=bool(row.has_simo_duplicate),
            simo_closings_count=simo_closings_count,
            banka_movements_count=banka_movements_count,
        )


class CreditMovementOut(Schema):
    """Um movimento de crédito do Banka atribuído a uma chave — a parcela do total."""

    id: str
    key: str
    date: date | None
    amount: float
    description: str | None

    @classmethod
    def from_row(cls, row: CreditMovement) -> CreditMovementOut:
        return cls(
            id=row.id,
            key=row.key,
            date=row.movement_date,
            amount=float(row.amount),
            description=row.description,
        )


class PendingCaseOut(Schema):
    """Caso de divergência para análise/regularização pelo operador."""

    id: str
    key: str
    pos_id: str
    period: int
    merchant: str
    account_number: str
    simo_amount: float
    banka_amount: float
    type: CaseType
    # A data limite é calculada pelo SPA, a partir de `first_date` e do prazo.
    first_date: date
    first_date_source: CaseDateSource
    e_ticket: str | None
    status: CaseStatusLabel
    # Desde quando está neste estado — «submetido à SIMO há 5 dias» sai daqui.
    status_since: date
    resolved_at: date | None
    # Mesma origem que em `ClosingDetailOut`.
    simo_closings_count: int
    banka_movements_count: int

    @classmethod
    def from_row(
        cls,
        row: PendingCase,
        simo_closings_count: int = 1,
        banka_movements_count: int = 1,
    ) -> PendingCaseOut:
        return cls(
            id=row.id,
            key=row.key,
            pos_id=row.pos_id,
            period=row.period,
            merchant=row.merchant,
            account_number=row.account_number,
            simo_amount=float(row.simo_amount),
            banka_amount=float(row.banka_amount),
            type=row.type,
            first_date=row.first_date,
            first_date_source=row.first_date_source,
            e_ticket=row.e_ticket,
            status=CASE_STATUS_LABELS[row.status],
            status_since=row.status_since,
            resolved_at=row.resolved_at,
            simo_closings_count=simo_closings_count,
            banka_movements_count=banka_movements_count,
        )


class ExecutionFilesOut(Schema):
    """Os nomes dos três ficheiros que deram origem à execução."""

    pos_list: str
    simo_closings: str
    banka_credits: str


class ValidationResultOut(Schema):
    """Uma execução persistida. Os detalhes vêm à parte, paginados."""

    execution_id: str
    executed_at: datetime
    period_start: date
    period_end: date
    report_name: str
    files: ExecutionFilesOut
    # O documento JSONB tal como foi gravado; a forma é do `ClosingSummary`.
    summary: dict[str, Any]
    cases: list[PendingCaseOut]

    @classmethod
    def from_row(
        cls,
        row: Execution,
        cases: list[PendingCase],
        key_counts: dict[str, tuple[int, int]],
    ) -> ValidationResultOut:
        return cls(
            execution_id=row.id,
            executed_at=row.executed_at,
            period_start=row.period_start,
            period_end=row.period_end,
            report_name=row.report_name,
            files=ExecutionFilesOut(
                pos_list=row.pos_list_file,
                simo_closings=row.simo_closings_file,
                banka_credits=row.banka_credits_file,
            ),
            summary=row.summary,
            cases=[
                PendingCaseOut.from_row(case, *key_counts.get(case.key, (1, 1))) for case in cases
            ],
        )


class ClosingMatchOut(Schema):
    """Um fecho da SIMO emparelhado com um movimento do Banka."""

    closing_id: str
    movement_id: str

    @classmethod
    def from_match(cls, match: ClosingMatch | Match) -> ClosingMatchOut:
        return cls(closing_id=match.closing_id, movement_id=match.movement_id)


class KeyBreakdownOut(Schema):
    """Os dois lados de uma chave — o que o painel de detalhe de um fecho mostra."""

    key: str
    closings: list[ClosingDetailOut]
    movements: list[CreditMovementOut]
    case: PendingCaseOut | None
    # Pares guardados e pares possíveis só pelo valor — ver `domain/matching.py`.
    matches: list[ClosingMatchOut]
    suggested_matches: list[ClosingMatchOut]

    @classmethod
    def from_parts(
        cls,
        key: str,
        closings: list[ClosingDetail],
        movements: list[CreditMovement],
        case: PendingCase | None,
        matches: list[ClosingMatch],
        suggested_matches: list[Match],
    ) -> KeyBreakdownOut:
        # As listas já vêm completas: a contagem não repete o `count_by_key`.
        simo_count, banka_count = len(closings), len(movements)
        return cls(
            key=key,
            closings=[ClosingDetailOut.from_row(row, simo_count, banka_count) for row in closings],
            movements=[CreditMovementOut.from_row(row) for row in movements],
            case=PendingCaseOut.from_row(case, simo_count, banka_count) if case else None,
            matches=[ClosingMatchOut.from_match(match) for match in matches],
            suggested_matches=[ClosingMatchOut.from_match(match) for match in suggested_matches],
        )


class DetailCountsOut(Schema):
    """Contagens dos chips — sobre toda a execução, não sobre a página."""

    all: int
    # Linhas dos fechos com duplicado na SIMO — o número do filtro, não um estado.
    simo_duplicates: int
    match: int
    mismatch: int
    missing: int
    zero: int
    duplicated: int


class DetailsPageOut(Schema):
    """Página da tabela de reconciliação — filtrada e contada no servidor."""

    items: list[ClosingDetailOut]
    page: int
    per_page: int
    # Ausentes a partir da segunda página: valem para a consulta, não para a página.
    total: int | None = None
    counts: DetailCountsOut | None = None


class CaseUpdateOut(Schema):
    """O caso como ficou, e o `summary` da execução já recalculado."""

    case: PendingCaseOut
    summary: dict[str, Any]


class CaseReconciliationOut(Schema):
    """O caso depois de conciliado, o `summary` recalculado e os pares que ficaram."""

    case: PendingCaseOut
    summary: dict[str, Any]
    matches: list[ClosingMatchOut]


class ReconciliationBatchOut(Schema):
    """Os casos conciliados de uma vez, e o `summary` já com todos eles."""

    cases: list[PendingCaseOut]
    summary: dict[str, Any]


class SlaSettingsOut(Schema):
    """O prazo de tratamento em vigor, e quem o pôs assim."""

    case_sla_days: int
    case_warning_days: int
    updated_at: datetime | None
    updated_by: str | None

    @classmethod
    def from_row(cls, row: SlaSettings) -> SlaSettingsOut:
        return cls(
            case_sla_days=row.case_sla_days,
            case_warning_days=row.case_warning_days,
            updated_at=row.updated_at,
            updated_by=row.updated_by,
        )


# ─── Entrada ─────────────────────────────────────────────────────────────────


class CasePatchIn(BaseModel):
    """O que o operador pode mudar num caso. Ambos opcionais: manda-se só um."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="ignore")

    status: str | None = None
    e_ticket: str | None = None


class ClosingMatchIn(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="ignore")

    closing_id: str
    movement_id: str


class SimoDuplicatesIn(BaseModel):
    """A decisão do operador sobre os fechos repetidos do export da SIMO."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="ignore")

    counted: bool


class CaseReconciliationIn(BaseModel):
    """Os pares de um caso, inteiros — substituem os que havia."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="ignore")

    matches: list[ClosingMatchIn]

    def to_matches(self) -> list[Match]:
        return [Match(item.closing_id, item.movement_id) for item in self.matches]


class ReconciliationItemIn(CaseReconciliationIn):
    """Os pares de um caso, dentro de uma conciliação em lote."""

    case_id: str


class ReconciliationBatchIn(BaseModel):
    """Vários casos, cada um com os seus pares inteiros. Entram todos ou nenhum."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="ignore")

    items: list[ReconciliationItemIn]


class SlaSettingsIn(BaseModel):
    """O prazo novo, inteiro — não em pedaços."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="ignore")

    case_sla_days: int
    case_warning_days: int
