"""Reconciliação SIMO ↔ Banka — o coração da automação.

Porte literal de `domain/reconciliation.py` do MozaOps v1.

Regra central: **as somas são agregadas por chave dos dois lados antes de
comparar**. Há chaves com vários fechos na SIMO e vários créditos no Banka (ex.:
a chave `231642323` tem 6 fechos e 8 movimentos); o VLOOKUP manual repetia o
mesmo crédito em cada linha e produzia falsas divergências. A validação é
calculada ao nível da chave e depois aplicada às linhas de detalhe.

**Não há prazo de crédito.** Um fecho pode ser creditado no próprio dia ou uma
semana depois, e continua a ser o crédito daquele fecho — todos os movimentos da
chave somam, aconteça isso quando acontecer.

Houve aqui uma janela de dias úteis que descartava o que caísse fora dela. Fazia
mais mal do que bem: nos ficheiros de Junho dava 72 chaves por «não creditado»
que o Banka tinha creditado pelo valor exacto, três dias depois. Tirá-la troca
esses 72 enganos por 1 — a chave `259342209`, onde um crédito de outro período
real do mesmo POS colide em `% 1000` e soma indevidamente. Setenta e dois contra
um, e o que fica é um valor a mais numa chave, não dinheiro dado por desaparecido.

Camada de domínio: sem I/O, sem framework — recebe estruturas já parseadas.
"""
from datetime import date
from decimal import Decimal

from .keys import build_key
from .models import (
    BankaCredit,
    ClosingDetail,
    ClosingSummary,
    CreditMovement,
    PendingCase,
    PosInfo,
    ReconciliationResult,
    SimoClosing,
    Validation,
)

MONTHS_PT = (
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
)

UNKNOWN = "—"


class NoClosingsError(Exception):
    """Nenhum fecho válido no ficheiro da SIMO — exceção de negócio do PDD."""


def build_report_name(start: date, end: date) -> str:
    """`FECHO_POS_DOP 21 a 28 de Junho-2026` (conteúdo em português)."""
    if start.month == end.month:
        return f"FECHO_POS_DOP {start.day} a {end.day} de {MONTHS_PT[end.month - 1]}-{end.year}"
    return (
        f"FECHO_POS_DOP {start.day} de {MONTHS_PT[start.month - 1]} "
        f"a {end.day} de {MONTHS_PT[end.month - 1]}-{end.year}"
    )


def reconcile(
    pos_list: dict[str, PosInfo],
    closings: list[SimoClosing],
    credits: dict[str, BankaCredit],
) -> ReconciliationResult:
    if not closings:
        raise NoClosingsError(
            "Dados incompletos ou em formato inválido: o ficheiro de Fechos SIMO "
            "não contém nenhum fecho válido."
        )

    closings, duplicates = _drop_duplicates(closings)
    simo_totals = _sum_by_key(closings)
    # Chaves com mais do que um fecho: não se somam nem se validam por soma — cada
    # fecho é observado individualmente (status «períodos duplicados»).
    duplicated_keys = _duplicated_keys(closings)
    # Guarda-se o movimento a movimento, para o operador poder abrir um fecho e ver
    # o lado do Banka em bruto, sem voltar ao MIS.
    movements = _audit_movements(credits, closings)
    validations = _validate_keys(simo_totals, credits, duplicated_keys)
    details = _build_details(closings, pos_list, credits, validations, simo_totals)
    cases = _build_cases(details, simo_totals, credits)
    summary = compute_summary(details, cases, simo_totals, credits, validations)
    summary.duplicatesDiscarded = duplicates
    summary.keyCollisions = _count_key_collisions(closings)
    summary.unregisteredPos = _count_unregistered(closings, pos_list)

    start = min(detail.simoClosingDate for detail in details)
    end = max(detail.simoClosingDate for detail in details)

    return ReconciliationResult(
        periodStart=start,
        periodEnd=end,
        reportName=build_report_name(start, end),
        details=details,
        cases=cases,
        summary=summary,
        movements=movements,
    )


def _drop_duplicates(closings: list[SimoClosing]) -> tuple[list[SimoClosing], int]:
    """Descarta linhas repetidas do export da SIMO — o mesmo fecho não conta duas vezes.

    O export do Portal repete ocasionalmente uma linha inteira. Somada duas
    vezes, inflaciona o total da chave e cria uma divergência falsa do valor
    exacto do fecho duplicado (visto em `262532/125`: 31 091,59 contado a
    dobrar contra um único crédito de 31 091,59 no Banka).

    A identidade é a linha completa — POS, período, data, nº de operações e
    total. Dois fechos genuínos do mesmo POS no mesmo dia diferem sempre em pelo
    menos um destes campos (ex.: `260300/397` em 21/06, operações 1 e 13).
    """
    unique: list[SimoClosing] = []
    seen: set[tuple[str, int, date, int, Decimal]] = set()
    for closing in closings:
        identity = (
            closing.posId,
            closing.period,
            closing.closingDate,
            closing.operationNumber,
            closing.total,
        )
        if identity in seen:
            continue
        seen.add(identity)
        unique.append(closing)
    return unique, len(closings) - len(unique)


def _count_key_collisions(closings: list[SimoClosing]) -> int:
    """Chaves que agregam mais do que um período bruto distinto.

    A chave usa `período % 1000` (o Banka trunca a 3 dígitos). Se o mesmo POS
    tiver, na mesma execução, períodos que colidem no módulo (ex.: 323 e 1323),
    os fechos somam-se numa só chave e produzem uma divergência falsa. Aqui não
    se corrige a soma — sinaliza-se a contagem para análise.
    """
    periods_by_key: dict[str, set[int]] = {}
    for closing in closings:
        key = build_key(closing.posId, closing.period)
        periods_by_key.setdefault(key, set()).add(closing.period)
    return sum(1 for periods in periods_by_key.values() if len(periods) > 1)


def _count_unregistered(
    closings: list[SimoClosing], pos_list: dict[str, PosInfo]
) -> int:
    """POS distintos com fechos mas sem linha na Lista de POS (comerciante '—')."""
    return len({closing.posId for closing in closings if closing.posId not in pos_list})


def _sum_by_key(closings: list[SimoClosing]) -> dict[str, Decimal]:
    totals: dict[str, Decimal] = {}
    for closing in closings:
        key = build_key(closing.posId, closing.period)
        totals[key] = totals.get(key, Decimal(0)) + closing.total
    return totals


def _duplicated_keys(closings: list[SimoClosing]) -> set[str]:
    """Chaves com mais do que um fecho SIMO (período repetido ou colisão % 1000).

    Estes não se somam: cada fecho é analisado individualmente pelo operador.
    """
    counts: dict[str, int] = {}
    for closing in closings:
        key = build_key(closing.posId, closing.period)
        counts[key] = counts.get(key, 0) + 1
    return {key for key, count in counts.items() if count > 1}


def _audit_movements(
    credits: dict[str, BankaCredit],
    closings: list[SimoClosing],
) -> list[CreditMovement]:
    """Movimento a movimento das chaves com fecho, para consulta no painel.

    Só as chaves com fecho SIMO entram: o ficheiro do MIS traz créditos de POS e
    períodos que não estão nesta execução, e esses não são alcançáveis pela tabela.
    """
    keys = {build_key(closing.posId, closing.period) for closing in closings}
    records: list[CreditMovement] = []
    for key in keys:
        credit = credits.get(key)
        if credit is None or not credit.movements:
            continue
        for movement in credit.movements:
            records.append(
                CreditMovement(
                    key=key,
                    date=movement.date,
                    amount=movement.amount,
                    description=movement.description,
                )
            )
    return records


def _validate_keys(
    simo_totals: dict[str, Decimal],
    credits: dict[str, BankaCredit],
    duplicated_keys: set[str],
) -> dict[str, tuple[Validation, Decimal | None]]:
    result: dict[str, tuple[Validation, Decimal | None]] = {}
    for key, simo_total in simo_totals.items():
        # Chave com >1 fecho: não se soma nem se compara — fica para análise manual.
        if key in duplicated_keys:
            result[key] = ("duplicated", None)
            continue
        credit = credits.get(key)
        banka_amount = credit.amount if credit else Decimal(0)
        # Fecho a 0,00 sem crédito (ou crédito 0,00): não há nada a conferir — é
        # um fecho zerado, não uma divergência. Sai da lista de casos pendentes.
        if simo_total == 0 and banka_amount == 0:
            result[key] = ("zero", Decimal(0))
            continue
        if credit is None:
            result[key] = ("missing", None)
            continue
        difference = credit.amount - simo_total
        # Igualdade EXACTA: os totais têm de ser taxativamente iguais para conferir
        # — sem tolerância de arredondamento.
        if difference == 0:
            result[key] = ("match", Decimal(0))
        else:
            result[key] = ("mismatch", difference)
    return result


def _build_details(
    closings: list[SimoClosing],
    pos_list: dict[str, PosInfo],
    credits: dict[str, BankaCredit],
    validations: dict[str, tuple[Validation, Decimal | None]],
    simo_totals: dict[str, Decimal],
) -> list[ClosingDetail]:
    details: list[ClosingDetail] = []
    for closing in closings:
        key = build_key(closing.posId, closing.period)
        info = pos_list.get(closing.posId)
        credit = credits.get(key)
        validation, difference = validations[key]
        details.append(
            ClosingDetail(
                posId=closing.posId,
                merchant=info.merchant if info else UNKNOWN,
                accountNumber=info.accountNumber if info else UNKNOWN,
                period=closing.period,
                key=key,
                simoClosingDate=closing.closingDate,
                operationNumber=closing.operationNumber,
                simoClosingTotal=closing.total,
                simoKeyTotal=simo_totals[key],
                closingDescription=credit.description if credit else None,
                bankaCreditDate=credit.creditDate if credit else None,
                bankaClosingTotal=credit.amount if credit else None,
                closingType=info.closingType if info else "NA",
                validation=validation,
                difference=difference,
            )
        )
    return details


def _build_cases(
    details: list[ClosingDetail],
    simo_totals: dict[str, Decimal],
    credits: dict[str, BankaCredit],
) -> list[PendingCase]:
    """Um caso por chave divergente — não um por fecho individual.

    Não geram caso: «match», fechos zerados («zero») e chaves com períodos
    duplicados («duplicated», que vão para análise manual, não para casos).
    """
    cases: list[PendingCase] = []
    seen: set[str] = set()
    for detail in details:
        if detail.validation in ("match", "zero", "duplicated") or detail.key in seen:
            continue
        seen.add(detail.key)
        credit = credits.get(detail.key)
        cases.append(
            PendingCase(
                key=detail.key,
                posId=detail.posId,
                period=detail.period,
                merchant=detail.merchant,
                accountNumber=detail.accountNumber,
                simoAmount=simo_totals.get(detail.key, Decimal(0)),
                bankaAmount=credit.amount if credit else Decimal(0),
                type="missing" if detail.validation == "missing" else "mismatch",
            )
        )
    return cases


def compute_summary(
    details: list[ClosingDetail],
    cases: list[PendingCase],
    simo_totals: dict[str, Decimal],
    credits: dict[str, BankaCredit],
    validations: dict[str, tuple[Validation, Decimal | None]],
) -> ClosingSummary:
    summary = ClosingSummary(processed=len(details), openCases=len(cases))

    for detail in details:
        if detail.validation == "match":
            summary.matched += 1
        elif detail.validation == "missing":
            summary.missingCount += 1
        elif detail.validation == "zero":
            summary.zeroClosings += 1
        elif detail.validation == "duplicated":
            summary.duplicatedPeriods += 1
        else:
            summary.mismatchCount += 1

    for key, (validation, _difference) in validations.items():
        simo_total = simo_totals.get(key, Decimal(0))
        credit = credits.get(key)
        banka_total = credit.amount if credit else Decimal(0)
        if validation == "match":
            summary.simoAmountMatched += simo_total
            summary.bankaAmountMatched += banka_total
        elif validation == "mismatch":
            summary.simoAmountMismatched += simo_total
            summary.bankaAmountMismatched += banka_total
            summary.divergenceAmount += abs(banka_total - simo_total)
        elif validation == "duplicated":
            # Não é divergência (não há soma a comparar), mas é dinheiro retido à
            # espera de análise — e o relatório lista-o entre o que falta tratar.
            # Guardam-se os dois lados: o Banka também duplica nestas chaves (tem
            # lá tantos movimentos como a SIMO tem fechos), logo há crédito feito.
            # Não o registar dava a chave por não creditada no apuramento.
            summary.simoAmountDuplicated += simo_total
            summary.bankaAmountDuplicated += banka_total
        elif validation == "zero":
            continue  # fecho zerado: não há crédito a esperar nem montante a somar
        else:
            summary.simoAmountMissing += simo_total
            summary.divergenceAmount += simo_total

    summary.divergent = summary.missingCount + summary.mismatchCount
    summary.validationRate = validation_rate(summary.matched, summary.processed)
    return summary


def validation_rate(matched: int, processed: int) -> float:
    """Taxa de validação, em percentagem com 1 decimal.

    O denominador é TUDO o que foi processado. Zerados e períodos duplicados não
    são divergência, mas também não conferem: excluí-los dava 100% com fechos por
    analisar, que é a única leitura que o operador não pode ter. E o arredondamento
    nunca sobe a 100,0% enquanto houver um fecho que não confere.
    """
    if not processed:
        return 0.0
    rate = round(matched / processed * 100, 1)
    return min(rate, 99.9) if matched < processed else rate
