"""Conciliação fecho a fecho: o que se sugere, o que se recusa, quando está feita.

Sem base de dados e sem HTTP — a regra do par é do domínio, e testa-se ali.
"""

from datetime import date
from decimal import Decimal

import pytest

from app.domain.errors import InvalidMatchError
from app.domain.matching import (
    Match,
    MatchEffect,
    MatchSide,
    is_fully_matched,
    match_effect,
    reconciled_summary,
    suggest_matches,
    validate_matches,
)


def side(id_: str, day: int | None, value: str) -> MatchSide:
    return MatchSide(id_, date(2026, 8, day) if day else None, Decimal(value))


# ─── Sugerir ─────────────────────────────────────────────────────────────────


def test_each_closing_takes_the_credit_with_the_same_amount() -> None:
    closings = [side("f1", 20, "300.00"), side("f2", 20, "7500.00")]
    credits = [side("m1", 21, "7500.00"), side("m2", 21, "300.00")]

    assert suggest_matches(closings, credits) == [Match("f1", "m2"), Match("f2", "m1")]


def test_repeated_amounts_pair_by_date_order() -> None:
    """O fecho mais antigo leva o crédito mais antigo — e a sugestão sai sempre igual."""
    closings = [side("f-tarde", 22, "3180.00"), side("f-cedo", 20, "3180.00")]
    credits = [side("m-tarde", 25, "3180.00"), side("m-cedo", 21, "3180.00")]

    assert suggest_matches(closings, credits) == [
        Match("f-cedo", "m-cedo"),
        Match("f-tarde", "m-tarde"),
    ]


def test_closing_without_same_amount_credit_stays_unmatched() -> None:
    closings = [side("f1", 20, "100.00"), side("f2", 20, "100.00")]
    credits = [side("m1", 21, "100.00")]

    suggestion = suggest_matches(closings, credits)

    assert suggestion == [Match("f1", "m1")]
    assert not is_fully_matched(suggestion, closings)


def test_one_cent_difference_is_not_a_match() -> None:
    """Igualdade exacta, como na reconciliação — sem tolerância."""
    assert suggest_matches([side("f1", 20, "100.00")], [side("m1", 21, "100.01")]) == []


def test_credit_without_date_goes_last() -> None:
    closings = [side("f1", 20, "50.00")]
    credits = [side("m-sem-data", None, "50.00"), side("m-datado", 21, "50.00")]

    assert suggest_matches(closings, credits) == [Match("f1", "m-datado")]


# ─── Validar ─────────────────────────────────────────────────────────────────


CLOSINGS = [side("f1", 20, "100.00"), side("f2", 20, "200.00")]
CREDITS = [side("m1", 21, "100.00"), side("m2", 21, "200.00"), side("m3", 22, "100.00")]


def test_valid_matches_pass() -> None:
    validate_matches([Match("f1", "m3"), Match("f2", "m2")], CLOSINGS, CREDITS)


@pytest.mark.parametrize(
    ("pairs", "message"),
    [
        ([Match("f1", "m2")], "valor exactamente igual"),
        ([Match("f1", "m1"), Match("f1", "m3")], "mesmo fecho"),
        ([Match("f1", "m1"), Match("f2", "m1")], "mesmo crédito"),
        ([Match("f9", "m1")], "não pertence a esta chave"),
        ([Match("f1", "m9")], "não pertence a esta chave"),
    ],
    ids=[
        "valor-diferente",
        "fecho-duas-vezes",
        "credito-duas-vezes",
        "fecho-alheio",
        "credito-alheio",
    ],
)
def test_impossible_matches_are_rejected_with_reason(pairs: list[Match], message: str) -> None:
    with pytest.raises(InvalidMatchError, match=message):
        validate_matches(pairs, CLOSINGS, CREDITS)


# ─── Quando está conciliado ──────────────────────────────────────────────────


def test_fully_matched_when_every_closing_has_a_pair_even_with_leftover_credits() -> None:
    """Numa colisão de `% 1000` a chave arrasta créditos de outro período."""
    assert is_fully_matched([Match("f1", "m1"), Match("f2", "m2")], CLOSINGS)


def test_without_closings_is_not_matched() -> None:
    assert not is_fully_matched([], [])


# ─── O que a conciliação muda no apuramento ─────────────────────────────────

SUMMARY = {
    "processed": 10,
    "matched": 7,
    "validationRate": 70.0,
    "duplicatedPeriods": 3,
    "simoAmountMatched": 1000.0,
    "bankaAmountMatched": 1000.0,
    "simoAmountDuplicated": 400.0,
    "bankaAmountDuplicated": 550.0,
}
NONE = MatchEffect(0, Decimal(0), Decimal(0))


def test_effect_counts_closings_and_both_amounts() -> None:
    effect = match_effect([Match("f1", "m3"), Match("f2", "m2")], CLOSINGS, CREDITS)

    assert effect == MatchEffect(2, Decimal("300.00"), Decimal("300.00"))


def test_reconciled_closings_move_from_duplicated_to_matched() -> None:
    """Um fecho ligado a um crédito igual confere — e a taxa acompanha."""
    after = MatchEffect(2, Decimal("300.00"), Decimal("300.00"))

    summary = reconciled_summary(SUMMARY, NONE, after)

    assert summary["matched"] == 9
    assert summary["duplicatedPeriods"] == 1
    assert summary["simoAmountMatched"] == pytest.approx(1300.0)
    assert summary["bankaAmountMatched"] == pytest.approx(1300.0)
    assert summary["simoAmountDuplicated"] == pytest.approx(100.0)
    assert summary["bankaAmountDuplicated"] == pytest.approx(250.0)
    assert summary["validationRate"] == 90.0


def test_saving_the_same_pairs_again_changes_nothing() -> None:
    """Aplica-se a diferença: o mesmo conjunto duas vezes não conta a dobrar."""
    effect = MatchEffect(2, Decimal("300.00"), Decimal("300.00"))

    assert reconciled_summary(SUMMARY, effect, effect) == SUMMARY


def test_undoing_a_pair_goes_back_to_duplicated() -> None:
    before = MatchEffect(2, Decimal("300.00"), Decimal("300.00"))
    after = MatchEffect(1, Decimal("100.00"), Decimal("100.00"))

    summary = reconciled_summary(SUMMARY, before, after)

    assert summary["matched"] == 6
    assert summary["duplicatedPeriods"] == 4
    assert summary["simoAmountDuplicated"] == pytest.approx(600.0)
