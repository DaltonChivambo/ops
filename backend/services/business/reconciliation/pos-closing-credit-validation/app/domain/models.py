"""Modelos de domínio da validação de crédito de fechos de POS.

Porte literal de `domain/models.py` do MozaOps v1. Estruturas puras — sem
FastAPI, sem SQLAlchemy, sem openpyxl. São o vocabulário que os parsers
produzem e que a reconciliação consome.
"""

from dataclasses import asdict, dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from .vocabulary import CaseType, ClosingType, Validation


def _to_camel(campo: str) -> str:
    """`simo_key_total` → `simoKeyTotal`.

    Escrito à mão para o domínio não passar a depender do Pydantic por causa de
    quatro linhas — é o mesmo motivo por que aqui não entra FastAPI nem openpyxl.
    """
    cabeca, *resto = campo.split("_")
    return cabeca + "".join(parte.capitalize() for parte in resto)


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


@dataclass(slots=True)
class BankaMovement:
    """Um movimento individual de crédito do Banka (uma linha do FECHO_POS)."""

    date: date | None
    amount: Decimal
    description: str | None


@dataclass(slots=True)
class BankaCredit:
    """Créditos do Banka de uma chave: soma dos movimentos + o detalhe por linha.

    `amount` soma TODOS os movimentos da chave, sem prazo: um fecho pode ser
    creditado no próprio dia ou uma semana depois, e continua a ser o crédito
    daquele fecho.

    Como o descritivo trunca o período a 3 dígitos, dois períodos reais distintos
    do mesmo POS podem cair na mesma chave e somar-se aqui. É o preço de não haver
    prazo, e é pequeno — ver a nota em `reconcile`.
    """

    amount: Decimal
    credit_date: date | None
    description: str | None
    movements: list["BankaMovement"] = field(default_factory=list)


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
    # Soma SIMO da chave — a parcela que o Banka credita e que entra na
    # `difference`. `simoClosingTotal` é só este fecho; comparar essa linha
    # com `bankaClosingTotal` (que é da chave) não fecha a conta.
    simo_key_total: Decimal
    closing_description: str | None
    banka_credit_date: date | None
    banka_closing_total: Decimal | None
    closing_type: ClosingType
    validation: Validation
    difference: Decimal | None


@dataclass(slots=True)
class PendingCase:
    """Caso de divergência para análise/regularização pelo operador."""

    key: str
    pos_id: str
    period: int
    merchant: str
    account_number: str
    simo_amount: Decimal
    banka_amount: Decimal
    type: CaseType


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
    # Fechos de valor 0,00 (sem crédito a esperar do Banka): não são divergência,
    # ficam fora dos casos pendentes, mas contam-se aqui para se saber que existem.
    zero_closings: int = 0
    # Fechos em chaves com >1 fecho (período repetido/colidido): não se somam,
    # ficam fora do match/mismatch e vão para análise manual individual.
    duplicated_periods: int = 0
    # Linhas repetidas no export da SIMO que foram descartadas antes de somar.
    duplicates_discarded: int = 0
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
    # Somas das chaves com períodos duplicados. Não é divergência — é o que está
    # retido à espera de análise manual, e vai ao relatório como tal. O Banka
    # duplica na mesma proporção da SIMO (a chave tem lá vários movimentos), por
    # isso há crédito a apontar-lhes: dá-lo por zero punha o montante todo como
    # dinheiro em falta, que é o contrário do que aconteceu.
    simo_amount_duplicated: Decimal = Decimal(0)
    banka_amount_duplicated: Decimal = Decimal(0)

    def to_json_dict(self) -> dict[str, Any]:
        """Os indicadores como documento JSON, que é a forma em que são guardados.

        A coluna `execution.summary` é JSONB e o frontend lê-a tal como está —
        logo esta é a forma canónica, e não uma representação da apresentação.

        **As chaves saem em camelCase, e não é descuido.** Os campos do Python
        são snake_case, mas este dicionário não é Python: é o documento que fica
        gravado na base e que o `models.ts` lê. Deixá-lo seguir a renomeação
        partia o SPA E desalinhava-o das execuções já gravadas, que estão em
        camelCase e não se migram por causa disto.
        """
        return {
            _to_camel(campo): float(valor) if isinstance(valor, Decimal) else valor
            for campo, valor in asdict(self).items()
        }


@dataclass(slots=True)
class CreditMovement:
    """Um movimento do Banka já atribuído a uma chave, para consulta posterior.

    O `ClosingDetail` guarda a SOMA do crédito da chave; isto guarda as parcelas.
    É o que permite ao operador abrir um fecho e ver de onde veio (ou não veio) o
    dinheiro, sem voltar ao MIS. Todos contam: não há prazo a partir do qual um
    crédito deixe de ser o crédito daquele fecho.
    """

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
