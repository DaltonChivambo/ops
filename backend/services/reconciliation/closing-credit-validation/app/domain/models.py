"""Modelos de domínio da validação de crédito de fechos de POS.

Porte literal de `domain/models.py` do MozaOps v1. Estruturas puras — sem
FastAPI, sem SQLAlchemy, sem openpyxl. São o vocabulário que os parsers
produzem e que a reconciliação consome.
"""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

Validation = str  # 'match' | 'mismatch' | 'missing' | 'zero' | 'duplicated'
ClosingType = str  # 'D' | 'D_PLUS_1' | 'NA'
CaseType = str  # 'missing' | 'mismatch'


@dataclass(slots=True)
class PosInfo:
    """Uma linha da Lista de POS do Portal SIMO."""

    merchant: str
    accountNumber: str
    closingType: ClosingType


@dataclass(slots=True)
class SimoClosing:
    """Um fecho registado no Portal SIMO."""

    posId: str
    period: int
    closingDate: date
    operationNumber: int
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
    creditDate: date | None
    description: str | None
    movements: list["BankaMovement"] = field(default_factory=list)


@dataclass(slots=True)
class ClosingDetail:
    """Uma linha da folha «Detalhes Validacao» — um fecho SIMO já validado."""

    posId: str
    merchant: str
    accountNumber: str
    period: int
    key: str
    simoClosingDate: date
    operationNumber: int
    simoClosingTotal: Decimal
    # Soma SIMO da chave — a parcela que o Banka credita e que entra na
    # `difference`. `simoClosingTotal` é só este fecho; comparar essa linha
    # com `bankaClosingTotal` (que é da chave) não fecha a conta.
    simoKeyTotal: Decimal
    closingDescription: str | None
    bankaCreditDate: date | None
    bankaClosingTotal: Decimal | None
    closingType: ClosingType
    validation: Validation
    difference: Decimal | None


@dataclass(slots=True)
class PendingCase:
    """Caso de divergência para análise/regularização pelo operador."""

    key: str
    posId: str
    period: int
    merchant: str
    accountNumber: str
    simoAmount: Decimal
    bankaAmount: Decimal
    type: CaseType


@dataclass(slots=True)
class ClosingSummary:
    """Indicadores do dashboard operacional (PDD §4.2.1)."""

    processed: int = 0
    matched: int = 0
    divergent: int = 0
    validationRate: float = 0.0
    divergenceAmount: Decimal = Decimal(0)
    openCases: int = 0
    resolvedCases: int = 0
    missingCount: int = 0
    mismatchCount: int = 0
    # Fechos de valor 0,00 (sem crédito a esperar do Banka): não são divergência,
    # ficam fora dos casos pendentes, mas contam-se aqui para se saber que existem.
    zeroClosings: int = 0
    # Fechos em chaves com >1 fecho (período repetido/colidido): não se somam,
    # ficam fora do match/mismatch e vão para análise manual individual.
    duplicatedPeriods: int = 0
    # Linhas repetidas no export da SIMO que foram descartadas antes de somar.
    duplicatesDiscarded: int = 0
    # Sinais de qualidade dos ficheiros de entrada (não bloqueiam a execução):
    #   keyCollisions — chaves que agregam >1 período bruto por colisão em % 1000.
    #   unregisteredPos — POS com fechos mas sem linha na Lista de POS (comerciante '—').
    keyCollisions: int = 0
    unregisteredPos: int = 0
    simoAmountMatched: Decimal = Decimal(0)
    bankaAmountMatched: Decimal = Decimal(0)
    simoAmountMismatched: Decimal = Decimal(0)
    bankaAmountMismatched: Decimal = Decimal(0)
    simoAmountMissing: Decimal = Decimal(0)
    # Somas das chaves com períodos duplicados. Não é divergência — é o que está
    # retido à espera de análise manual, e vai ao relatório como tal. O Banka
    # duplica na mesma proporção da SIMO (a chave tem lá vários movimentos), por
    # isso há crédito a apontar-lhes: dá-lo por zero punha o montante todo como
    # dinheiro em falta, que é o contrário do que aconteceu.
    simoAmountDuplicated: Decimal = Decimal(0)
    bankaAmountDuplicated: Decimal = Decimal(0)


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

    periodStart: date
    periodEnd: date
    reportName: str
    details: list[ClosingDetail] = field(default_factory=list)
    cases: list[PendingCase] = field(default_factory=list)
    summary: ClosingSummary = field(default_factory=ClosingSummary)
    movements: list[CreditMovement] = field(default_factory=list)
