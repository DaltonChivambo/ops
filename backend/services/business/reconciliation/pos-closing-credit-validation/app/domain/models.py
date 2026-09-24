"""Modelos de domínio da validação de crédito de fechos de POS."""

from dataclasses import asdict, dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from .vocabulary import CaseDateSource, CaseType, ClosingType, Validation


def _to_camel(field_name: str) -> str:
    """`simo_key_total` → `simoKeyTotal`."""
    head, *rest = field_name.split("_")
    return head + "".join(part.capitalize() for part in rest)


@dataclass(slots=True)
class PosInfo:
    """Uma linha da Lista de POS do Portal SIMO."""

    merchant: str
    account_number: str
    closing_type: ClosingType


@dataclass(slots=True)
class SimoClosing:
    """Um fecho registado no Portal SIMO."""

    pos_id: str
    period: int
    closing_date: date
    operation_number: int
    total: Decimal
    # A linha do export tal como veio; vazia quando o fecho não vem de ficheiro.
    row: tuple[str, ...] = ()


@dataclass(slots=True)
class BankaMovement:
    """Um movimento individual de crédito do Banka (uma linha do FECHO_POS)."""

    date: date | None
    amount: Decimal
    description: str | None


@dataclass(slots=True)
class BankaCredit:
    """Créditos do Banka de uma chave: soma dos movimentos + o detalhe por linha."""

    amount: Decimal
    credit_date: date | None
    description: str | None
    movements: list[BankaMovement] = field(default_factory=list)


@dataclass(slots=True)
class ClosingDetail:
    """Uma linha da folha «Detalhes Validacao» — um fecho SIMO já validado."""

    pos_id: str
    merchant: str
    account_number: str
    period: int
    key: str
    simo_closing_date: date
    operation_number: int
    simo_closing_total: Decimal
    # Soma SIMO da chave. `simoClosingTotal` é só este fecho e não fecha a conta.
    simo_key_total: Decimal
    closing_description: str | None
    banka_credit_date: date | None
    banka_closing_total: Decimal | None
    closing_type: ClosingType
    validation: Validation
    difference: Decimal | None
    # Linha repetida no export: conta como fecho, com a validação da original.
    simo_duplicate: bool = False
    # A original de uma linha duplicada na SIMO — para a tabela as pôr juntas.
    has_simo_duplicate: bool = False


@dataclass(slots=True)
class PendingCase:
    """Caso aberto para análise ou regularização pelo operador."""

    key: str
    pos_id: str
    period: int
    merchant: str
    account_number: str
    simo_amount: Decimal
    banka_amount: Decimal
    type: CaseType
    # Primeira data da chave, do lado que for; daqui conta o prazo (`domain/sla.py`).
    first_date: date
    first_date_source: CaseDateSource


@dataclass(slots=True)
class ClosingSummary:
    """Indicadores do dashboard operacional (PDD §4.2.1)."""

    processed: int = 0
    matched: int = 0
    divergent: int = 0
    validation_rate: float = 0.0
    divergence_amount: Decimal = Decimal(0)
    open_cases: int = 0
    resolved_cases: int = 0
    missing_count: int = 0
    mismatch_count: int = 0
    # Fechos a 0,00: não são divergência e ficam fora dos casos pendentes.
    zero_closings: int = 0
    # Chaves com >1 fecho SIMO, ou 1 fecho e >1 movimento Banka: análise manual.
    duplicated_periods: int = 0
    # Repetidos do export: entram em `processed`, nunca nos estados nem na taxa.
    duplicates_discarded: int = 0
    # O que somam do lado SIMO; entra no apuramento só com `count_simo_duplicates`.
    simo_amount_duplicate_rows: Decimal = Decimal(0)
    # O crédito do Banka correspondente — ver `_duplicate_rows_credit`.
    banka_amount_duplicate_rows: Decimal = Decimal(0)
    # Decisão da execução inteira: não mexe em estados, casos nem taxa.
    count_simo_duplicates: bool = False
    # Movimentos com N_DOCUMENTO repetido em chaves com fecho SIMO. Contam como
    # créditos, e a chave vai para análise. As execuções antigas guardaram em vez
    # disto `bankaDuplicatesDiscarded`, quando os repetidos se fundiam num só.
    banka_repeated_movements: int = 0
    # Sinais de qualidade dos ficheiros de entrada (não bloqueiam a execução):
    #   keyCollisions — chaves que agregam >1 período bruto por colisão em % 1000.
    #   unregisteredPos — POS com fechos mas sem linha na Lista de POS (comerciante '—').
    key_collisions: int = 0
    unregistered_pos: int = 0
    simo_amount_matched: Decimal = Decimal(0)
    banka_amount_matched: Decimal = Decimal(0)
    simo_amount_mismatched: Decimal = Decimal(0)
    banka_amount_mismatched: Decimal = Decimal(0)
    simo_amount_missing: Decimal = Decimal(0)
    # Somas das chaves com períodos repetidos: retido à espera de análise manual.
    simo_amount_duplicated: Decimal = Decimal(0)
    banka_amount_duplicated: Decimal = Decimal(0)

    def to_json_dict(self) -> dict[str, Any]:
        """Os indicadores como documento JSON, que é a forma em que são guardados."""
        return {
            _to_camel(field_name): float(value) if isinstance(value, Decimal) else value
            for field_name, value in asdict(self).items()
        }


@dataclass(slots=True)
class CreditMovement:
    """Um movimento do Banka já atribuído a uma chave, para consulta posterior."""

    key: str
    date: date | None
    amount: Decimal
    description: str | None


@dataclass(slots=True)
class ReconciliationResult:
    """Resultado completo de uma execução, antes de ser persistido."""

    period_start: date
    period_end: date
    report_name: str
    details: list[ClosingDetail] = field(default_factory=list)
    cases: list[PendingCase] = field(default_factory=list)
    summary: ClosingSummary = field(default_factory=ClosingSummary)
    movements: list[CreditMovement] = field(default_factory=list)
