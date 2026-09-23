"""A ordem por que o operador lê a tabela de fechos.

Estava numa expressão `CASE` no `ORDER BY` e passou a uma coluna. A regra é a
mesma, e é aqui que se prova que continua a ser — uma troca silenciosa reordena
a tabela inteira sem partir mais nada.
"""

import pytest

from app.domain.vocabulary import Validation
from app.repositories.execution_repository import sort_rank

NEITHER = {"simo_duplicate": False, "has_simo_duplicate": False}


@pytest.mark.parametrize(
    ("validation", "expected"),
    [
        (Validation.MISMATCH, 0),
        (Validation.MISSING, 1),
        (Validation.DUPLICATED, 2),
        (Validation.MATCH, 4),
        (Validation.ZERO, 5),
    ],
)
def test_each_state_keeps_its_place(validation, expected):
    assert sort_rank(validation, **NEITHER) == expected


@pytest.mark.parametrize("validation", [Validation.MATCH, Validation.ZERO])
@pytest.mark.parametrize("mark", ["simo_duplicate", "has_simo_duplicate"])
def test_repeated_closings_gather_in_one_block(validation, mark):
    assert sort_rank(validation, **{**NEITHER, mark: True}) == 3


@pytest.mark.parametrize(
    "validation", [Validation.MISMATCH, Validation.MISSING, Validation.DUPLICATED]
)
@pytest.mark.parametrize("mark", ["simo_duplicate", "has_simo_duplicate"])
def test_what_needs_work_wins_over_the_repeated_mark(validation, mark):
    """A precedência do `CASE`: os três primeiros ramos decidem antes da marca."""
    assert sort_rank(validation, **{**NEITHER, mark: True}) == sort_rank(validation, **NEITHER)


def test_the_order_is_the_one_the_operator_reads():
    states = [
        Validation.MISMATCH,
        Validation.MISSING,
        Validation.DUPLICATED,
        Validation.MATCH,
        Validation.ZERO,
    ]
    ranks = [sort_rank(state, **NEITHER) for state in states]
    assert ranks == sorted(ranks)
