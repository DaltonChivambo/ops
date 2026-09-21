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
esses 72 enganos por um risco novo — a chave `259342209`, onde um crédito de
outro período real do mesmo POS colide em `% 1000` e soma indevidamente ao
lado do Banka. Um só fecho na SIMO, mas dois movimentos no Banka de datas bem
diferentes (um antes do fecho, outro depois): não é o crédito daquele fecho a
sair errado, é a chave a levar dinheiro de outro período. Por isso uma chave só
conta como incorrecta quando os DOIS lados têm uma linha só — um fecho na SIMO
e um movimento no Banka — e mesmo assim não bate. Mais que um movimento no
Banka (ou mais que um fecho na SIMO) é ambiguidade a desfazer manualmente, não
uma divergência: fica «períodos repetidos», ao lado da chave com vários fechos.

Camada de domínio: sem I/O, sem framework — recebe estruturas já parseadas.
"""

from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from typing import Any

from .errors import NoClosingsError
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
)
from .vocabulary import CaseDateSource, CaseType, ClosingType, Validation

MONTHS_PT = (
    "Janeiro",
    "Fevereiro",
    "Março",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
)

UNKNOWN = "—"


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

    closings, simo_duplicates = _split_simo_duplicates(closings, credits)
    simo_totals = _sum_by_key(closings)
    # Chaves com mais do que um fecho: não se somam nem se validam por soma — cada
    # fecho é observado individualmente (status «períodos repetidos»).
    duplicated_keys = _duplicated_keys(closings)
    # Guarda-se o movimento a movimento, para o operador poder abrir um fecho e ver
    # o lado do Banka em bruto, sem voltar ao MIS.
    movements = _audit_movements(credits, closings)
    validations = _validate_keys(simo_totals, credits, duplicated_keys)
    details = _build_details(closings, pos_list, credits, validations, simo_totals)
    cases = _build_cases(details, simo_totals, credits)
    summary = compute_summary(details, cases, simo_totals, credits, validations)
    # As linhas duplicadas na SIMO não são anomalia: entram no total de fechos, numa
    # linha própria, e não nos estados (nem no que está por tratar) nem na taxa.
    # Ficam nos detalhes, marcadas, com a validação da original; não abrem caso
    # nem entram na soma da chave, que é o mesmo fecho.
    details += _simo_duplicate_details(closings, details, simo_duplicates)
    summary.duplicates_discarded = len(simo_duplicates)
    # Os dois lados dos fechos repetidos, para o apuramento os poder contar se o
    # operador o mandar. Ficam calculados sempre: é informação dos ficheiros,
    # não uma decisão.
    summary.simo_amount_duplicate_rows = sum(
        (duplicate.total for duplicate in simo_duplicates), Decimal(0)
    )
    summary.banka_amount_duplicate_rows = _duplicate_rows_credit(simo_duplicates, credits)
    summary.processed += len(simo_duplicates)
    summary.key_collisions = _count_key_collisions(closings)
    summary.unregistered_pos = _count_unregistered(closings, pos_list)

    start = min(detail.simo_closing_date for detail in details)
    end = max(detail.simo_closing_date for detail in details)

    return ReconciliationResult(
        period_start=start,
        period_end=end,
        report_name=build_report_name(start, end),
        details=details,
        cases=cases,
        summary=summary,
        movements=movements,
    )


def _duplicate_rows_credit(
    duplicates: list[SimoClosing],
    credits: dict[str, BankaCredit],
) -> Decimal:
    """O crédito do Banka que corresponde aos fechos repetidos da SIMO.

    Um fecho repetido é cópia de um fecho que o Banka creditou. O crédito que
    lhe corresponde é, portanto, o dele próprio — limitado pelo que a chave tem
    mesmo creditado: numa chave sem crédito nenhum não há correspondência que
    mostrar, e o fecho repetido fica em diferença.

    **Este crédito já está contado na linha do estado da chave.** Mostrá-lo aqui
    outra vez é deliberado: a SIMO também conta a linha duas vezes, e é assim
    que os dois lados ficam simétricos e a diferença do total passa a ser a
    verdadeira da execução, em vez de uma criada pelo ficheiro vir com linhas a
    dobrar. Em contrapartida, a soma da coluna do Banka deixa de ser o dinheiro
    que o banco pagou — é por isso que contar os repetidos é uma decisão do
    operador e não o comportamento normal.
    """
    by_key: dict[str, Decimal] = {}
    for duplicate in duplicates:
        key = build_key(duplicate.pos_id, duplicate.period)
        by_key[key] = by_key.get(key, Decimal(0)) + duplicate.total

    covered = Decimal(0)
    for key, repeated in by_key.items():
        credit = credits.get(key)
        covered += min(repeated, credit.amount) if credit else Decimal(0)
    return covered


def _split_simo_duplicates(
    closings: list[SimoClosing], credits: dict[str, BankaCredit]
) -> tuple[list[SimoClosing], list[SimoClosing]]:
    """Separa os fechos repetidos do export da SIMO dos fechos verdadeiros.

    O export do Portal repete às vezes uma linha inteira. Somada duas vezes,
    inflaciona a chave e cria uma divergência falsa do valor exacto do fecho
    (visto em `262532/125`: 31 091,59 contado a dobrar contra um único crédito
    de 31 091,59 no Banka).

    Uma linha só é duplicada na SIMO com as duas provas:

    1. **É igual a outra em todas as colunas do ficheiro** — Id Comerciante, POS,
       período, data, nº de operações, total e o resto. Sem a linha em bruto
       (fechos que não vêm de um ficheiro), vale POS, período, data, nº de
       operações e total.
    2. **O Banka não a creditou tantas vezes.** Se a chave tem tantos créditos
       daquele valor como fechos repetidos, são fechos verdadeiros com o mesmo
       valor — ficam todos, e a chave vai a períodos repetidos, para conciliar.

    Das linhas iguais ficam tantas quantas o Banka creditou (pelo menos uma); as
    outras são as cópias.
    """
    groups: dict[tuple[object, ...], list[SimoClosing]] = {}
    for closing in closings:
        groups.setdefault(_identity(closing), []).append(closing)

    genuine: dict[tuple[object, ...], int] = {}
    for identity, group in groups.items():
        if len(group) == 1:
            genuine[identity] = 1
            continue
        first = group[0]
        credit = credits.get(build_key(first.pos_id, first.period))
        credited = sum(1 for m in credit.movements if m.amount == first.total) if credit else 0
        genuine[identity] = max(1, min(len(group), credited))

    kept: list[SimoClosing] = []
    duplicates: list[SimoClosing] = []
    seen: dict[tuple[object, ...], int] = {}
    for closing in closings:
        identity = _identity(closing)
        seen[identity] = seen.get(identity, 0) + 1
        (kept if seen[identity] <= genuine[identity] else duplicates).append(closing)
    return kept, duplicates


def _identity(closing: SimoClosing) -> tuple[object, ...]:
    """O que faz de duas linhas a mesma — a linha em bruto, ou os campos do fecho.

    Os espaços de cada célula colapsam antes de comparar. O `cell_text` já apara
    as pontas, mas um espaço a mais no meio — ou um espaço não-quebrável, que os
    portais web deixam cair no texto — dava duas identidades diferentes, e a
    linha repetida passava a um segundo fecho da chave. Não somava mal, porque
    uma chave com dois fechos vai para análise manual, mas mandava o operador
    conciliar à mão o que era só sujidade do ficheiro.
    """
    if closing.row:
        return tuple(" ".join(cell.split()) for cell in closing.row)
    return (
        closing.pos_id,
        closing.period,
        closing.closing_date,
        closing.operation_number,
        closing.total,
    )


def _simo_duplicate_details(
    closings: list[SimoClosing], details: list[ClosingDetail], duplicates: list[SimoClosing]
) -> list[ClosingDetail]:
    """Cada linha duplicada como cópia da linha da original, marcada."""
    original = {_identity(c): d for c, d in zip(closings, details, strict=True)}
    copies: list[ClosingDetail] = []
    for duplicate in duplicates:
        source = original[_identity(duplicate)]
        source.has_simo_duplicate = True
        copies.append(replace(source, simo_duplicate=True, has_simo_duplicate=False))
    return copies


def _count_key_collisions(closings: list[SimoClosing]) -> int:
    """Chaves que agregam mais do que um período bruto distinto.

    A chave usa `período % 1000` (o Banka trunca a 3 dígitos). Se o mesmo POS
    tiver, na mesma execução, períodos que colidem no módulo (ex.: 323 e 1323),
    os fechos somam-se numa só chave e produzem uma divergência falsa. Aqui não
    se corrige a soma — sinaliza-se a contagem para análise.
    """
    periods_by_key: dict[str, set[int]] = {}
    for closing in closings:
        key = build_key(closing.pos_id, closing.period)
        periods_by_key.setdefault(key, set()).add(closing.period)
    return sum(1 for periods in periods_by_key.values() if len(periods) > 1)


def _count_unregistered(closings: list[SimoClosing], pos_list: dict[str, PosInfo]) -> int:
    """POS distintos com fechos mas sem linha na Lista de POS (comerciante '—')."""
    return len({closing.pos_id for closing in closings if closing.pos_id not in pos_list})


def _sum_by_key(closings: list[SimoClosing]) -> dict[str, Decimal]:
    totals: dict[str, Decimal] = {}
    for closing in closings:
        key = build_key(closing.pos_id, closing.period)
        totals[key] = totals.get(key, Decimal(0)) + closing.total
    return totals


def _duplicated_keys(closings: list[SimoClosing]) -> set[str]:
    """Chaves com mais do que um fecho SIMO (período repetido ou colisão % 1000).

    Estes não se somam: cada fecho é analisado individualmente pelo operador.
    """
    counts: dict[str, int] = {}
    for closing in closings:
        key = build_key(closing.pos_id, closing.period)
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
    keys = {build_key(closing.pos_id, closing.period) for closing in closings}
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
            result[key] = (Validation.DUPLICATED, None)
            continue
        credit = credits.get(key)
        banka_amount = credit.amount if credit else Decimal(0)
        # Fecho a 0,00 sem crédito (ou crédito 0,00): não há nada a conferir — é
        # um fecho zerado, não uma divergência. Sai da lista de casos pendentes.
        if simo_total == 0 and banka_amount == 0:
            result[key] = (Validation.ZERO, Decimal(0))
            continue
        if credit is None:
            result[key] = (Validation.MISSING, None)
            continue
        difference = credit.amount - simo_total
        # Igualdade EXACTA: os totais têm de ser taxativamente iguais para conferir
        # — sem tolerância de arredondamento.
        if difference == 0:
            result[key] = (Validation.MATCH, Decimal(0))
        elif len(credit.movements) > 1:
            # A chave não bate, mas o Banka tem mais de um movimento — pode ser
            # um crédito de outro período real a colidir na mesma chave (ver a
            # nota no topo do ficheiro), não necessariamente um erro do fecho.
            # Só conta «incorrecto» a chave com uma linha só de cada lado.
            result[key] = (Validation.DUPLICATED, None)
        else:
            result[key] = (Validation.MISMATCH, difference)
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
        key = build_key(closing.pos_id, closing.period)
        info = pos_list.get(closing.pos_id)
        credit = credits.get(key)
        validation, difference = validations[key]
        details.append(
            ClosingDetail(
                pos_id=closing.pos_id,
                merchant=info.merchant if info else UNKNOWN,
                account_number=info.account_number if info else UNKNOWN,
                period=closing.period,
                key=key,
                simo_closing_date=closing.closing_date,
                operation_number=closing.operation_number,
                simo_closing_total=closing.total,
                simo_key_total=simo_totals[key],
                closing_description=credit.description if credit else None,
                banka_credit_date=credit.credit_date if credit else None,
                banka_closing_total=credit.amount if credit else None,
                closing_type=info.closing_type if info else ClosingType.NA,
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
    """Um caso por chave que pede tratamento — não um por fecho individual.

    Não geram caso: «match» e fechos zerados («zero»). Os períodos repetidos
    também abrem caso, um por chave, tal como não-creditados e incorrectos —
    é aí que o operador desfaz a ambiguidade de qual fecho é o real.

    O caso leva a primeira data da chave — o fecho mais antigo da SIMO ou o
    primeiro crédito do Banka, o que for anterior — e diz de que lado ela veio.
    É dela que conta o prazo de tratamento. Empate fica para a SIMO: no mesmo
    dia, o fecho vem antes do crédito que lhe corresponde.

    O detalhe representativo continua a ser o primeiro (o `seen`) e não o mais
    antigo — numa colisão de `período % 1000` os detalhes diferem no período,
    e trocá-lo mudava o que a linha do caso mostra.
    """
    earliest_simo: dict[str, date] = {}
    for detail in details:
        current = earliest_simo.get(detail.key)
        if current is None or detail.simo_closing_date < current:
            earliest_simo[detail.key] = detail.simo_closing_date

    cases: list[PendingCase] = []
    seen: set[str] = set()
    for detail in details:
        if detail.validation in (Validation.MATCH, Validation.ZERO) or detail.key in seen:
            continue
        seen.add(detail.key)
        credit = credits.get(detail.key)

        # `credit.credit_date` já é o primeiro movimento da chave (ver o parser
        # dos créditos), por isso basta compará-lo com o fecho mais antigo.
        first_date = earliest_simo[detail.key]
        first_date_source = CaseDateSource.SIMO
        credited_on = credit.credit_date if credit else None
        if credited_on is not None and credited_on < first_date:
            first_date = credited_on
            first_date_source = CaseDateSource.BANKA

        if detail.validation is Validation.MISSING:
            case_type = CaseType.MISSING
        elif detail.validation is Validation.DUPLICATED:
            case_type = CaseType.DUPLICATED
        else:
            case_type = CaseType.MISMATCH
        cases.append(
            PendingCase(
                key=detail.key,
                pos_id=detail.pos_id,
                period=detail.period,
                merchant=detail.merchant,
                account_number=detail.account_number,
                simo_amount=simo_totals.get(detail.key, Decimal(0)),
                banka_amount=credit.amount if credit else Decimal(0),
                type=case_type,
                first_date=first_date,
                first_date_source=first_date_source,
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
    summary = ClosingSummary(processed=len(details), open_cases=len(cases))

    for detail in details:
        if detail.validation is Validation.MATCH:
            summary.matched += 1
        elif detail.validation is Validation.MISSING:
            summary.missing_count += 1
        elif detail.validation is Validation.ZERO:
            summary.zero_closings += 1
        elif detail.validation is Validation.DUPLICATED:
            summary.duplicated_periods += 1
        else:
            summary.mismatch_count += 1

    for key, (validation, _difference) in validations.items():
        simo_total = simo_totals.get(key, Decimal(0))
        credit = credits.get(key)
        banka_total = credit.amount if credit else Decimal(0)
        if validation is Validation.MATCH:
            summary.simo_amount_matched += simo_total
            summary.banka_amount_matched += banka_total
        elif validation is Validation.MISMATCH:
            summary.simo_amount_mismatched += simo_total
            summary.banka_amount_mismatched += banka_total
            summary.divergence_amount += abs(banka_total - simo_total)
        elif validation is Validation.DUPLICATED:
            # Não é divergência (não há soma a comparar), mas é dinheiro retido à
            # espera de análise — e o relatório lista-o entre o que falta tratar.
            # Guardam-se os dois lados: o Banka também duplica nestas chaves (tem
            # lá tantos movimentos como a SIMO tem fechos), logo há crédito feito.
            # Não o registar dava a chave por não creditada no apuramento.
            #
            # **O lado do Banka nunca passa o da SIMO.** A conciliação parte dos
            # fechos: um crédito só conta na medida em que há fecho que ele possa
            # pagar. Nestas chaves há a mais, porque um período real diferente do
            # mesmo POS colide em `% 1000` e traz dinheiro que não é desta chave
            # (ver a nota no topo). Deixá-lo entrar punha o Banka acima da SIMO no
            # total, que é dizer que o banco pagou fechos que não existem.
            summary.simo_amount_duplicated += simo_total
            summary.banka_amount_duplicated += min(banka_total, simo_total)
        elif validation is Validation.ZERO:
            continue  # fecho zerado: não há crédito a esperar nem montante a somar
        else:
            summary.simo_amount_missing += simo_total
            summary.divergence_amount += simo_total

    summary.divergent = summary.missing_count + summary.mismatch_count
    summary.validation_rate = validation_rate(summary.matched, summary.processed)
    return summary


# Onde o peso de uma chave cai no `summary`, por estado. `None` é o lado que
# aquele estado não tem: um fecho não creditado não tem montante do Banka.
_COUNT_FIELD = {
    Validation.MATCH: "matched",
    Validation.MISMATCH: "mismatchCount",
    Validation.MISSING: "missingCount",
    Validation.ZERO: "zeroClosings",
    Validation.DUPLICATED: "duplicatedPeriods",
}
_SIMO_FIELD = {
    Validation.MATCH: "simoAmountMatched",
    Validation.MISMATCH: "simoAmountMismatched",
    Validation.MISSING: "simoAmountMissing",
    Validation.ZERO: None,
    Validation.DUPLICATED: "simoAmountDuplicated",
}
_BANKA_FIELD = {
    Validation.MATCH: "bankaAmountMatched",
    Validation.MISMATCH: "bankaAmountMismatched",
    Validation.MISSING: None,
    Validation.ZERO: None,
    Validation.DUPLICATED: "bankaAmountDuplicated",
}


@dataclass(frozen=True, slots=True)
class KeyTally:
    """Uma chave COM fechos repetidos, tal como está gravada.

    A validação é a que os próprios fechos repetidos levam — que é a da chave
    deles — e vem de lá como está, sem se revalidar nada. `simo` e `banka` são
    os totais da chave sem eles; `repeated` e `repeated_amount`, o que eles são.
    """

    validation: Validation
    simo: Decimal
    banka: Decimal
    repeated: int
    repeated_amount: Decimal


@dataclass(frozen=True, slots=True)
class _Weight:
    """Quanto uma chave pesa no apuramento, com ou sem os fechos repetidos."""

    closings: int
    simo: Decimal
    banka: Decimal
    divergence: Decimal


def _weight(key: KeyTally, include_repeated: bool) -> _Weight:
    extra = key.repeated_amount if include_repeated else Decimal(0)
    simo = key.simo + extra
    # Do lado do Banka entra o crédito que corresponde aos fechos repetidos: o
    # mesmo valor deles, limitado ao que a chave tem creditado. Numa chave não
    # creditada não há correspondência, e o repetido engrossa o que falta.
    banka = key.banka + min(extra, key.banka)
    # O Banka nunca passa a SIMO numa chave de períodos repetidos — ver a nota
    # em `compute_summary`.
    if key.validation is Validation.DUPLICATED:
        banka = min(banka, simo)

    if key.validation is Validation.MISMATCH:
        divergence = abs(banka - simo)
    elif key.validation is Validation.MISSING:
        divergence = simo
    else:
        divergence = Decimal(0)
    return _Weight(
        closings=key.repeated if include_repeated else 0,
        simo=simo,
        banka=banka,
        divergence=divergence,
    )


def with_simo_duplicates(
    summary: dict[str, Any], keys: Iterable[KeyTally], counted: bool
) -> dict[str, Any]:
    """O `summary` com os fechos repetidos da SIMO dentro, ou fora, do apuramento.

    Um fecho repetido não é um fecho novo e por isso **não tem estado próprio**:
    o estado dela é o da chave. Mandada contar, conta aí — em «crédito confere»
    se a chave confere, em «creditado incorrectamente» se não confere, e assim
    por diante. Não há linha à parte, porque não há estado à parte.

    Conta dos dois lados. Do lado da SIMO entra o que a linha vale; do lado do
    Banka, o crédito que lhe corresponde. Contar só um deles abria uma
    divergência que não existe.

    Aplica-se a DIFERENÇA entre o antes e o depois, chave a chave, e só nas
    chaves que têm fechos repetidos. Nada mais no documento se toca — nem o que
    as conciliações já lá acertaram, nem os estados, nem os casos.
    """
    updated = dict(summary)
    for key in keys:
        before = _weight(key, include_repeated=not counted)
        after = _weight(key, include_repeated=counted)
        _shift(updated, _COUNT_FIELD[key.validation], after.closings - before.closings)
        _shift(updated, _SIMO_FIELD[key.validation], after.simo - before.simo)
        _shift(updated, _BANKA_FIELD[key.validation], after.banka - before.banka)
        _shift(updated, "divergenceAmount", after.divergence - before.divergence)

    updated["countSimoDuplicates"] = counted
    updated["divergent"] = updated.get("mismatchCount", 0) + updated.get("missingCount", 0)
    # Denominador da taxa: as repetidas só entram nele quando contam — a mesma
    # conta que `matching.reconciled_summary` faz.
    processed = int(updated.get("processed", 0))
    if not counted:
        processed -= int(updated.get("duplicatesDiscarded", 0))
    updated["validationRate"] = validation_rate(int(updated.get("matched", 0)), processed)
    return updated


def _shift(summary: dict[str, Any], field: str | None, delta: int | Decimal) -> None:
    """Soma ao campo, no tipo em que ele está gravado. `None` e zero não mexem."""
    if field is None or delta == 0:
        return
    if isinstance(delta, int):
        summary[field] = int(summary.get(field, 0)) + delta
        return
    summary[field] = float(Decimal(str(summary.get(field, 0))) + delta)


def validation_rate(matched: int, processed: int) -> float:
    """Taxa de validação, em percentagem com 1 decimal.

    O denominador é TUDO o que foi processado. Zerados e períodos repetidos não
    são divergência, mas também não conferem: excluí-los dava 100% com fechos por
    analisar, que é a única leitura que o operador não pode ter. E o arredondamento
    nunca sobe a 100,0% enquanto houver um fecho que não confere.
    """
    if not processed:
        return 0.0
    rate = round(matched / processed * 100, 1)
    return min(rate, 99.9) if matched < processed else rate
