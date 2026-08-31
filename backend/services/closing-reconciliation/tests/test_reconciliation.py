"""Teste de paridade do domínio contra os ficheiros reais de referência.

Os `.xlsx` são dados bancários reais (ver aviso no README da raiz) e nunca são
versionados — `*.xlsx` está no `.gitignore` da raiz. Este teste salta-se
sozinho quando `tests/fixtures/` não os tem (ex.: CI, ou um checkout sem os
ficheiros de amostra). Os números esperados vêm de
`docs/implementation-plan.md` §8 (verificação ponta a ponta), que por sua vez
os verificou contra o manual do PDD.
"""
from pathlib import Path

import pytest

from app.domain.reconciliation import reconcile
from app.infra import parsers

FIXTURES = Path(__file__).parent / "fixtures"
POS_LIST = FIXTURES / "pos-list.xlsx"
SIMO_CLOSINGS = FIXTURES / "simo-closings.xlsx"
BANKA_CREDITS = FIXTURES / "banka-credits.xlsx"

pytestmark = pytest.mark.skipif(
    not (POS_LIST.exists() and SIMO_CLOSINGS.exists() and BANKA_CREDITS.exists()),
    reason="ficheiros de amostra reais não estão em tests/fixtures/ (dados bancários, não versionados)",
)


def _reconcile_fixtures():
    with POS_LIST.open("rb") as stream:
        pos_list = parsers.parse_pos_list(stream, POS_LIST.name)
    with SIMO_CLOSINGS.open("rb") as stream:
        closings = parsers.parse_simo_closings(stream, SIMO_CLOSINGS.name)
    with BANKA_CREDITS.open("rb") as stream:
        credits = parsers.parse_banka_credits(stream, BANKA_CREDITS.name)
    return reconcile(pos_list, closings, credits)


def test_summary_matches_reference_numbers():
    result = _reconcile_fixtures()
    summary = result.summary

    assert summary.processed == 18_138
    assert summary.validationRate == 99.3
    assert summary.missingCount == 118
    assert summary.mismatchCount == 1
    assert summary.duplicatedPeriods == 16
    assert float(summary.simoAmountMissing) == 1_021_564.32
    assert float(summary.simoAmountMatched) == 543_350_098.30
    assert float(summary.bankaAmountMatched) == 543_350_098.30


def test_known_collision_key_is_a_mismatch_not_missing():
    """A chave `259342209`: colisão real em `% 1000` — ver o comentário em
    `domain/reconciliation.py` sobre a janela de crédito removida."""
    result = _reconcile_fixtures()
    detail = next(d for d in result.details if d.key == "259342209")

    assert detail.validation == "mismatch"
    assert float(detail.difference) == 6_641.0


def test_cases_are_one_per_divergent_key():
    result = _reconcile_fixtures()
    assert len(result.cases) == result.summary.missingCount + result.summary.mismatchCount
