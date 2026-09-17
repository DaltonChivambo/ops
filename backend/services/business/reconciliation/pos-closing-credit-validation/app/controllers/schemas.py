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
from decimal import Decimal
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
    """Base de todos os modelos de saída.

    Os campos são snake_case porque são Python; o JSON sai em camelCase
    porque é o contrato do `models.ts`. O alias faz a ponte, e o
    `populate_by_name` deixa construí-los pelo nome do campo — que é como o
    código os escreve.

    `extra="forbid"` porque um campo a mais numa resposta é sempre engano.
    """

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
    # Nº de fechos SIMO / movimentos Banka desta chave — não vêm da linha (não
    # são colunas persistidas, ver `ExecutionRepository.count_by_key`), por
    # isso `from_row` recebe-os à parte. `1, 1` por omissão: só interessam
    # quando `validation` é `duplicated`, e desfazem aí a ambiguidade entre
    # duplicação do lado SIMO, do lado Banka, ou de ambos.
    simo_closings_count: int
    banka_movements_count: int
    # Créditos do Banka sem fecho por analisar nesta chave — quantos e quanto.
    # Também à parte da linha, como as contagens acima; zero em quase todas.
    unmatched_credits: int
    banka_amount_unmatched: float

    @classmethod
    def from_row(
        cls,
        row: ClosingDetail,
        simo_closings_count: int = 1,
        banka_movements_count: int = 1,
        unmatched_credits: int = 0,
        banka_amount_unmatched: Decimal = Decimal(0),
    ) -> "ClosingDetailOut":
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
            simo_closings_count=simo_closings_count,
            banka_movements_count=banka_movements_count,
            unmatched_credits=unmatched_credits,
            banka_amount_unmatched=float(banka_amount_unmatched),
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
    # A data limite não vem daqui: é `first_date` mais o prazo em vigor, e quem
    # a calcula é o SPA, que já traz as definições e sabe que dia é hoje.
    first_date: date
    first_date_source: CaseDateSource
    e_ticket: str | None
    status: CaseStatusLabel
    # Desde quando está neste estado — «submetido à SIMO há 5 dias» sai daqui.
    status_since: date
    resolved_at: date | None
    # Ver o comentário equivalente em `ClosingDetailOut` — mesma origem e
    # omissão a `1, 1`.
    simo_closings_count: int
    banka_movements_count: int

    @classmethod
    def from_row(
        cls,
        row: PendingCase,
        simo_closings_count: int = 1,
        banka_movements_count: int = 1,
    ) -> "PendingCaseOut":
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
    # Não é tipado campo a campo de propósito: é o documento JSONB tal como foi
    # gravado, e o `ClosingSummary` do domínio é que manda na sua forma. Tipá-lo
    # aqui obrigava a manter duas listas de 24 campos em dia uma com a outra.
    summary: dict[str, Any]
    cases: list[PendingCaseOut]

    @classmethod
    def from_row(
        cls,
        row: Execution,
        cases: list[PendingCase],
        key_counts: dict[str, tuple[int, int]],
    ) -> "ValidationResultOut":
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
    def from_match(cls, match: ClosingMatch | Match) -> "ClosingMatchOut":
        return cls(closing_id=match.closing_id, movement_id=match.movement_id)


class KeyBreakdownOut(Schema):
    """Os dois lados de uma chave — o que o painel de detalhe de um fecho mostra."""

    key: str
    closings: list[ClosingDetailOut]
    movements: list[CreditMovementOut]
    case: PendingCaseOut | None
    # Os pares já guardados, e os que se podem fazer só pelo valor — ver
    # `domain/matching.py`. O ecrã só os usa nas chaves de períodos duplicados.
    matches: list[ClosingMatchOut]
    suggested_matches: list[ClosingMatchOut]
    # O último dia do intervalo da execução: um crédito de depois dele não é um
    # crédito sem fecho desta execução — ver `within_period`.
    period_end: date

    @classmethod
    def from_parts(
        cls,
        period_end: date,
        key: str,
        closings: list[ClosingDetail],
        movements: list[CreditMovement],
        case: PendingCase | None,
        matches: list[ClosingMatch],
        suggested_matches: list[Match],
    ) -> "KeyBreakdownOut":
        # As duas listas já vêm completas (ver `list_details_by_key`/
        # `list_movements_by_key`), por isso a contagem é grátis aqui — sem
        # repetir a query que `count_by_key` faz para as listas paginadas.
        simo_count, banka_count = len(closings), len(movements)
        return cls(
            key=key,
            closings=[ClosingDetailOut.from_row(row, simo_count, banka_count) for row in closings],
            movements=[CreditMovementOut.from_row(row) for row in movements],
            case=PendingCaseOut.from_row(case, simo_count, banka_count) if case else None,
            matches=[ClosingMatchOut.from_match(match) for match in matches],
            suggested_matches=[ClosingMatchOut.from_match(match) for match in suggested_matches],
            period_end=period_end,
        )


class DetailCountsOut(Schema):
    """Contagens dos chips — sobre toda a execução, não sobre a página."""

    all: int
    # Fechos das chaves com crédito sem fecho — o número do filtro, não um estado.
    unmatched: int
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
    per_page: int
    counts: DetailCountsOut


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
    def from_row(cls, row: SlaSettings) -> "SlaSettingsOut":
        return cls(
            case_sla_days=row.case_sla_days,
            case_warning_days=row.case_warning_days,
            updated_at=row.updated_at,
            updated_by=row.updated_by,
        )


# ─── Entrada ─────────────────────────────────────────────────────────────────


class CasePatchIn(BaseModel):
    """O que o operador pode mudar num caso. Ambos opcionais: manda-se só um.

    O `status` fica `str` e não `Literal` de propósito — quem sabe que estados
    existem e como se passa de um para o outro é o domínio, e é ele que devolve
    a mensagem em português quando o valor não serve. Validá-lo aqui trocava
    essa mensagem por uma do Pydantic.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="ignore")

    status: str | None = None
    e_ticket: str | None = None


class ClosingMatchIn(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="ignore")

    closing_id: str
    movement_id: str


class CaseReconciliationIn(BaseModel):
    """Os pares de um caso, inteiros — substituem os que havia.

    Uma lista vazia é um pedido válido: desfaz a conciliação da chave. As
    regras do par (valor igual, cada lado uma vez) são do domínio, que devolve
    a mensagem em português — não se validam aqui.
    """

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
    """O prazo novo, inteiro — não em pedaços.

    Os limites ficam no domínio (`domain/sla.py`) e não em `Field(ge=...)`: o
    invariante que interessa é «o aviso vem antes do prazo», e esse compara
    dois campos. Validado num sítio só, devolve a mensagem em português.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="ignore")

    case_sla_days: int
    case_warning_days: int
