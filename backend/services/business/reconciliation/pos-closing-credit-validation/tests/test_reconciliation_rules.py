"""As regras da reconciliação, com dados inventados.

O `test_reconciliation.py` prova os números contra os ficheiros reais do
departamento — mas esses são dados bancários, não são versionados, e saltam-se
sozinhos em qualquer checkout que não os tenha (CI incluído). Ou seja: o
algoritmo que dá valor a esta automação podia ser mexido sem que nada
protestasse.

Estes exercitam as MESMAS regras com números pequenos e inventados, e correm
sempre. Não substituem a prova de paridade — dizem que a regra está lá, não que
os 18 138 fechos de Junho dão o que davam.

Cada teste nomeia a regra que fixa, e as regras são as documentadas em
`domain/reconciliation.py`.
"""

from datetime import date
from decimal import Decimal

from app.domain.models import BankaCredit, BankaMovement, PosInfo, SimoClosing
from app.domain.reconciliation import (
    KeyTally,
    build_report_name,
    reconcile,
    validation_rate,
    with_simo_duplicates,
)
from app.domain.vocabulary import CaseDateSource, CaseType, ClosingType, Validation

DAY = date(2026, 6, 23)


def pos(**changes: object) -> dict[str, PosInfo]:
    base = {"merchant": "Comerciante", "account_number": "000123", "closing_type": ClosingType.D}
    return {"200001": PosInfo(**{**base, **changes})}  # type: ignore[arg-type]


def closing(
    pos_id: str = "200001", period: int = 101, total: str = "100.00", ops: int = 1, day: date = DAY
) -> SimoClosing:
    return SimoClosing(
        pos_id=pos_id, period=period, closing_date=day, operation_number=ops, total=Decimal(total)
    )


def credit(*amounts: str) -> BankaCredit:
    movements = [
        BankaMovement(date=DAY, amount=Decimal(m), description="P24-Fecho TPA 0000200001 - 101")
        for m in amounts
    ]
    return BankaCredit(
        amount=sum((m.amount for m in movements), Decimal(0)),
        credit_date=DAY,
        description=movements[0].description,
        movements=movements,
    )


# ─── Os cinco estados ────────────────────────────────────────────────────────


def test_matches_when_key_totals_are_exactly_equal() -> None:
    r = reconcile(pos(), [closing(total="100.00")], {"200001101": credit("100.00")})

    assert r.details[0].validation is Validation.MATCH
    assert r.details[0].difference == Decimal(0)
    assert r.cases == []


def test_one_cent_difference_is_already_mismatch() -> None:
    """Igualdade EXACTA: não há tolerância de arredondamento."""
    r = reconcile(pos(), [closing(total="100.00")], {"200001101": credit("100.01")})

    assert r.details[0].validation is Validation.MISMATCH
    assert r.details[0].difference == Decimal("0.01")
    assert r.cases[0].type is CaseType.MISMATCH


def test_no_credit_at_all_is_missing() -> None:
    r = reconcile(pos(), [closing(total="100.00")], {})

    assert r.details[0].validation is Validation.MISSING
    assert r.details[0].difference is None
    assert r.details[0].banka_closing_total is None
    assert r.cases[0].type is CaseType.MISSING
    assert r.summary.simo_amount_missing == Decimal("100.00")


def test_zero_closing_without_credit_is_zero_not_divergence() -> None:
    r = reconcile(pos(), [closing(total="0.00")], {})

    assert r.details[0].validation is Validation.ZERO
    assert r.cases == [], "um fecho zerado não pede tratamento a ninguém"
    assert r.summary.divergent == 0


def test_two_closings_on_same_key_open_single_duplicated_case() -> None:
    closings = [closing(total="100.00", ops=1), closing(total="200.00", ops=2)]

    r = reconcile(pos(), closings, {"200001101": credit("300.00")})

    assert [d.validation for d in r.details] == [Validation.DUPLICATED] * 2
    # Um caso por chave, não um por fecho — mesmo dedup que missing/mismatch.
    assert len(r.cases) == 1
    assert r.cases[0].type is CaseType.DUPLICATED
    assert r.cases[0].simo_amount == Decimal("300.00")
    assert r.cases[0].banka_amount == Decimal("300.00")
    assert r.summary.duplicated_periods == 2
    # Os dois lados registam-se: o Banka duplica na mesma proporção da SIMO.
    assert r.summary.simo_amount_duplicated == Decimal("300.00")
    assert r.summary.banka_amount_duplicated == Decimal("300.00")


def test_single_closing_many_banka_movements_is_duplicated_not_mismatch() -> None:
    """Um crédito de outro período real do mesmo POS pode colidir na chave (ver
    a nota no topo de `domain/reconciliation.py`): a chave não bate, mas com
    mais de um movimento no Banka não é o fecho a estar mal creditado — é
    ambiguidade a desfazer manualmente, tal como a chave com vários fechos."""
    r = reconcile(pos(), [closing(total="2599.00")], {"200001101": credit("6641.00", "2599.00")})

    assert r.details[0].validation is Validation.DUPLICATED
    assert r.details[0].difference is None
    assert r.cases[0].type is CaseType.DUPLICATED
    assert r.summary.mismatch_count == 0
    assert r.summary.duplicated_periods == 1


def test_one_closing_credited_twice_with_its_value_goes_to_analysis() -> None:
    """Dois créditos iguais ao fecho: em dobro ou exportado duas vezes, decide a análise."""
    r = reconcile(pos(), [closing(total="100.00")], {"200001101": credit("100.00", "100.00")})

    assert r.details[0].validation is Validation.DUPLICATED
    assert r.cases[0].type is CaseType.DUPLICATED
    assert r.cases[0].banka_amount == Decimal("200.00")
    assert r.summary.matched == 0


def test_one_closing_one_movement_not_equal_is_mismatch() -> None:
    """Só conta «incorrecto» a chave com uma linha só de cada lado."""
    r = reconcile(pos(), [closing(total="2599.00")], {"200001101": credit("9240.00")})

    assert r.details[0].validation is Validation.MISMATCH
    assert r.details[0].difference == Decimal("6641.00")
    assert r.cases[0].type is CaseType.MISMATCH


def test_case_takes_the_oldest_closing_date_of_the_key() -> None:
    """O prazo conta do fecho que está à espera há mais tempo, não do último."""
    before = date(2026, 6, 20)
    closings = [
        closing(total="100.00", ops=2, day=DAY),
        closing(total="200.00", ops=1, day=before),
    ]

    r = reconcile(pos(), closings, {"200001101": credit("300.00")})

    assert r.cases[0].first_date == before
    assert r.cases[0].first_date_source is CaseDateSource.SIMO


def test_single_closing_case_takes_that_closing_date() -> None:
    r = reconcile(pos(), [closing(total="100.00")], {})

    assert r.cases[0].first_date == DAY
    assert r.cases[0].first_date_source is CaseDateSource.SIMO


# ─── De que lado vem a primeira data ─────────────────────────────────────────


def test_credit_before_closing_drives_the_deadline() -> None:
    """A primeira data é a primeira, venha de que lado vier."""
    before = date(2026, 6, 20)
    early_credit = BankaCredit(
        amount=Decimal("100.01"),
        credit_date=before,
        description="P24-Fecho TPA 0000200001 - 101",
        movements=[BankaMovement(date=before, amount=Decimal("100.01"), description=None)],
    )

    r = reconcile(pos(), [closing(total="100.00", day=DAY)], {"200001101": early_credit})

    assert r.cases[0].first_date == before
    assert r.cases[0].first_date_source is CaseDateSource.BANKA


def test_same_day_closing_wins_over_credit() -> None:
    """Empate fica para a SIMO: o fecho vem antes do crédito que lhe corresponde."""
    r = reconcile(pos(), [closing(total="100.00", day=DAY)], {"200001101": credit("100.01")})

    assert r.cases[0].first_date == DAY
    assert r.cases[0].first_date_source is CaseDateSource.SIMO


def test_without_credit_date_is_always_simo() -> None:
    r = reconcile(pos(), [closing(total="100.00")], {})

    assert r.cases[0].first_date_source is CaseDateSource.SIMO


# ─── A regra central: somar por chave antes de comparar ──────────────────────


def test_comparison_is_per_key_not_per_row() -> None:
    """Vários fechos e vários créditos na mesma chave somam-se dos dois lados.

    É esta a regra que o VLOOKUP manual não tinha: ele repetia o mesmo crédito
    em cada linha e produzia divergências falsas.
    """
    closings = [
        closing(pos_id="200001", period=101, total="60.00", ops=1),
        closing(pos_id="200001", period=102, total="40.00", ops=2),
    ]
    credits = {"200001101": credit("60.00"), "200001102": credit("25.00", "15.00")}

    r = reconcile(pos(), closings, credits)

    assert {d.key: d.validation for d in r.details} == {
        "200001101": Validation.MATCH,
        "200001102": Validation.MATCH,
    }


def test_one_case_per_divergent_key_not_per_closing() -> None:
    closings = [closing(period=101, total="10.00"), closing(period=102, total="20.00")]

    r = reconcile(pos(), closings, {})

    assert len(r.cases) == 2
    assert {c.key for c in r.cases} == {"200001101", "200001102"}


def test_key_truncates_period_to_three_digits() -> None:
    """O Banka cicla o contador em módulo 1000 — ver `domain/keys.py`."""
    r = reconcile(pos(), [closing(period=4540, total="10.00")], {})

    assert r.details[0].key == "200001540"


# ─── Higiene dos ficheiros de entrada ────────────────────────────────────────


def test_repeated_simo_export_row_does_not_count_twice() -> None:
    """Somada a dobrar, inflacionava a chave e criava uma divergência falsa."""
    # A identidade é a linha COMPLETA: POS, período, data, nº de operações e total.
    row = {"total": "100.00", "ops": 3}
    r = reconcile(pos(), [closing(**row), closing(**row)], {"200001101": credit("100.00")})  # type: ignore[arg-type]

    assert r.summary.duplicates_discarded == 1
    # Conta no total de fechos, numa linha própria; o estado conta o fecho uma vez.
    assert r.summary.processed == 2
    assert r.summary.matched == 1
    assert r.summary.validation_rate == 100.0
    assert [(d.validation, d.simo_duplicate, d.has_simo_duplicate) for d in r.details] == [
        (Validation.MATCH, False, True),
        (Validation.MATCH, True, False),
    ]
    # O montante da chave soma o fecho uma vez.
    assert r.summary.simo_amount_matched == Decimal("100.00")


def test_same_line_twice_credited_twice_is_two_real_closings() -> None:
    """O Banka creditou as duas: não é cópia, são dois fechos com o mesmo valor."""
    row = {"total": "100.00", "ops": 3}
    r = reconcile(
        pos(),
        [closing(**row), closing(**row)],  # type: ignore[arg-type]
        {"200001101": credit("100.00", "100.00")},
    )

    assert r.summary.duplicates_discarded == 0
    assert [d.validation for d in r.details] == [Validation.DUPLICATED, Validation.DUPLICATED]


def test_extra_whitespace_does_not_hide_a_repeated_line() -> None:
    """Sujidade do ficheiro não pode virar um segundo fecho da chave."""
    a = closing(total="100.00", ops=3)
    b = closing(total="100.00", ops=3)
    # Escritos assim e não com os caracteres lá dentro: um espaço a mais e um
    # não-quebrável são invisíveis no código, e o teste parecia comparar iguais.
    nbsp = "\u00a0"
    a.row = ("200001", "MERCADO ABC", "101")
    b.row = ("200001", f"MERCADO{nbsp} ABC", "101")

    r = reconcile(pos(), [a, b], {"200001101": credit("100.00")})

    assert r.summary.duplicates_discarded == 1
    assert [d.validation for d in r.details] == [Validation.MATCH, Validation.MATCH]


def test_lines_differing_in_any_file_column_are_not_repeated() -> None:
    """Iguais nos campos do fecho, mas diferentes noutra coluna do ficheiro: não é cópia."""
    a = closing(total="100.00", ops=3)
    b = closing(total="100.00", ops=3)
    a.row = ("200001", "101", "x")
    b.row = ("200001", "101", "y")

    r = reconcile(pos(), [a, b], {"200001101": credit("100.00")})

    assert r.summary.duplicates_discarded == 0


# ─── O Banka nunca passa a SIMO ──────────────────────────────────────────────


def test_banka_side_of_a_repeated_key_never_exceeds_what_simo_closed() -> None:
    """A conciliação parte dos fechos: crédito sem fecho que o pague não conta.

    Nestas chaves o Banka traz por vezes dinheiro a mais — um período real
    diferente do mesmo POS que colide em `% 1000`. Deixá-lo entrar punha o
    Banka acima da SIMO no total, que é dizer que o banco pagou fechos que não
    existem (visto em `217745596`: 29 900,00 fechados contra 60 440,00).
    """
    closings = [closing(period=101, total="100.00"), closing(period=1101, total="50.00")]

    r = reconcile(pos(), closings, {"200001101": credit("400.00", "300.00")})

    assert r.summary.duplicated_periods == 2
    assert r.summary.simo_amount_duplicated == Decimal("150.00")
    assert r.summary.banka_amount_duplicated == Decimal("150.00")


def test_banka_side_of_a_repeated_key_keeps_what_falls_short() -> None:
    """Limitar é um tecto, não um acerto: a menos continua a ser a menos."""
    closings = [closing(period=101, total="100.00"), closing(period=1101, total="50.00")]

    r = reconcile(pos(), closings, {"200001101": credit("40.00", "30.00")})

    assert r.summary.simo_amount_duplicated == Decimal("150.00")
    assert r.summary.banka_amount_duplicated == Decimal("70.00")


# ─── O montante dos fechos repetidos da SIMO ─────────────────────────────────


def test_repeated_simo_lines_carry_their_own_amount() -> None:
    """Fica apurado à parte: é o que a reconciliação de montantes conta, ou não."""
    row = {"total": "100.00", "ops": 3}
    r = reconcile(pos(), [closing(**row), closing(**row)], {"200001101": credit("100.00")})  # type: ignore[arg-type]

    assert r.summary.simo_amount_duplicate_rows == Decimal("100.00")
    # O estado não sabe disto: a chave tem um fecho só e confere.
    assert r.summary.matched == 1
    assert r.summary.simo_amount_matched == Decimal("100.00")
    assert r.summary.duplicated_periods == 0


def test_repeated_line_carries_the_credit_that_paid_the_original() -> None:
    """A repetida é cópia de um fecho creditado: o crédito que lhe corresponde é o dela."""
    row = {"total": "100.00", "ops": 3}
    r = reconcile(pos(), [closing(**row), closing(**row)], {"200001101": credit("100.00")})  # type: ignore[arg-type]

    assert r.summary.duplicates_discarded == 1
    assert r.summary.simo_amount_duplicate_rows == Decimal("100.00")
    # Os dois lados iguais: contar o fecho repetido não abre diferença nenhuma.
    assert r.summary.banka_amount_duplicate_rows == Decimal("100.00")


def test_repeated_line_on_an_uncredited_key_has_no_correspondence() -> None:
    """Sem crédito na chave não há correspondência: a repetida fica em diferença."""
    row = {"total": "100.00", "ops": 3}
    r = reconcile(pos(), [closing(**row), closing(**row)], {})  # type: ignore[arg-type]

    assert r.summary.simo_amount_duplicate_rows == Decimal("100.00")
    assert r.summary.banka_amount_duplicate_rows == Decimal(0)


def test_correspondence_never_exceeds_what_the_repeated_lines_are_worth() -> None:
    """Crédito a mais na chave é problema de outra linha, não das repetidas."""
    row = {"total": "100.00", "ops": 3}
    r = reconcile(pos(), [closing(**row), closing(**row)], {"200001101": credit("900.00")})  # type: ignore[arg-type]

    assert r.summary.banka_amount_duplicate_rows == Decimal("100.00")


def test_without_repeated_lines_the_amount_is_zero() -> None:
    r = reconcile(pos(), [closing(total="100.00")], {"200001101": credit("100.00")})

    assert r.summary.simo_amount_duplicate_rows == Decimal(0)
    assert r.summary.banka_amount_duplicate_rows == Decimal(0)
    assert r.summary.count_simo_duplicates is False


# ─── Contar os fechos repetidos no apuramento ────────────────────────────────


def _summary_of(*closings_and_credits: object) -> dict[str, object]:
    """O `summary` de uma execução, como fica gravado."""
    closings, credits = closings_and_credits  # type: ignore[misc]
    return reconcile(pos(), closings, credits).summary.to_json_dict()  # type: ignore[arg-type]


def test_counted_repeated_lines_land_in_the_state_of_their_key() -> None:
    """Não têm estado próprio: contam onde a chave já está, aqui em «confere»."""
    row = {"total": "100.00", "ops": 3}
    summary = _summary_of([closing(**row), closing(**row)], {"200001101": credit("100.00")})  # type: ignore[arg-type]
    key = KeyTally(Validation.MATCH, Decimal("100.00"), Decimal("100.00"), 1, Decimal("100.00"))

    counted = with_simo_duplicates(summary, [key], True)

    assert counted["matched"] == 2
    # Os dois lados sobem juntos: contá-las não abre divergência nenhuma.
    assert counted["simoAmountMatched"] == 200.0
    assert counted["bankaAmountMatched"] == 200.0
    assert counted["countSimoDuplicates"] is True
    # Não aparece em «períodos repetidos», que é outro estado e outro problema.
    assert counted["duplicatedPeriods"] == 0


def test_counting_and_uncounting_gets_back_to_the_same_numbers() -> None:
    row = {"total": "100.00", "ops": 3}
    summary = _summary_of([closing(**row), closing(**row)], {"200001101": credit("100.00")})  # type: ignore[arg-type]
    key = KeyTally(Validation.MATCH, Decimal("100.00"), Decimal("100.00"), 1, Decimal("100.00"))

    back = with_simo_duplicates(with_simo_duplicates(summary, [key], True), [key], False)

    assert back == summary


def test_counted_repeated_line_on_an_uncredited_key_grows_what_is_missing() -> None:
    """Sem crédito na chave não há correspondência: a repetida engrossa a falta."""
    summary = {
        "missingCount": 1,
        "simoAmountMissing": 100.0,
        "divergenceAmount": 100.0,
        "processed": 2,
        "matched": 0,
        "mismatchCount": 0,
        "duplicatesDiscarded": 1,
    }
    key = KeyTally(Validation.MISSING, Decimal("100.00"), Decimal(0), 1, Decimal("100.00"))

    counted = with_simo_duplicates(summary, [key], True)

    assert counted["missingCount"] == 2
    assert counted["simoAmountMissing"] == 200.0
    assert counted["divergenceAmount"] == 200.0
    assert counted["divergent"] == 2


def test_unregistered_pos_gets_dash_and_is_counted() -> None:
    r = reconcile({}, [closing(total="10.00")], {})

    assert r.details[0].merchant == "—"
    assert r.details[0].account_number == "—"
    assert r.details[0].closing_type is ClosingType.NA
    assert r.summary.unregistered_pos == 1


def test_periods_colliding_on_modulo_are_flagged() -> None:
    """323 e 1323 caem na mesma chave; não se corrige a soma, conta-se."""
    closings = [
        closing(period=323, total="10.00", ops=1),
        closing(period=1323, total="20.00", ops=2),
    ]

    r = reconcile(pos(), closings, {})

    assert r.summary.key_collisions == 1


def test_banka_movements_are_kept_one_by_one() -> None:
    r = reconcile(pos(), [closing(total="100.00")], {"200001101": credit("60.00", "40.00")})

    assert [m.amount for m in r.movements] == [Decimal("60.00"), Decimal("40.00")]
    assert all(m.key == "200001101" for m in r.movements)


# ─── Indicadores ─────────────────────────────────────────────────────────────


def test_rate_never_rounds_to_100_while_a_closing_does_not_match() -> None:
    assert validation_rate(999, 1000) == 99.9
    assert validation_rate(1000, 1000) == 100.0
    assert validation_rate(0, 0) == 0.0


def test_rate_denominator_is_everything_processed() -> None:
    """Zerados e duplicados não conferem — excluí-los dava 100% com trabalho por fazer."""
    closings = [closing(period=101, total="10.00"), closing(period=102, total="0.00")]

    r = reconcile(pos(), closings, {"200001101": credit("10.00")})

    assert r.summary.processed == 2
    assert r.summary.matched == 1
    assert r.summary.zero_closings == 1
    assert r.summary.validation_rate == 50.0


def test_report_period_comes_from_closing_dates() -> None:
    closings = [
        closing(period=101, total="10.00", day=date(2026, 6, 21)),
        closing(period=102, total="10.00", day=date(2026, 6, 28)),
    ]

    r = reconcile(pos(), closings, {})

    assert r.period_start == date(2026, 6, 21)
    assert r.period_end == date(2026, 6, 28)
    assert r.report_name == "FECHO_POS_DOP 21 a 28 de Junho-2026"


def test_report_name_spans_months() -> None:
    assert (
        build_report_name(date(2026, 5, 28), date(2026, 6, 3))
        == "FECHO_POS_DOP 28 de Maio a 3 de Junho-2026"
    )
