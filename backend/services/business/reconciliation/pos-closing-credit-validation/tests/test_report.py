"""O relatório Excel: o que cai em cada folha, e se as folhas fecham entre si.

O DOP lê o relatório, não a API — um número errado aqui é um número errado no
fecho do departamento, mesmo com a reconciliação certa. Por isso os testes não
olham só para células soltas: obrigam as três folhas a baterem umas com as
outras, que é a conferência que o operador faria à mão.

Um cenário só, com um fecho de cada situação, a passar pela reconciliação real.
"""

from dataclasses import asdict
from datetime import date
from decimal import Decimal
from io import BytesIO
from types import SimpleNamespace
from typing import Any

import pytest
from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet

from app.domain.models import BankaCredit, BankaMovement, PosInfo, SimoClosing
from app.domain.reconciliation import reconcile
from app.domain.vocabulary import ClosingType
from app.infrastructure.excel.report import build_workbook

DIA = date(2026, 6, 23)

# Colunas (a A fica vazia em todas as folhas).
DETAILS_SIMO, DETAILS_BANKA, DETAILS_VALIDATION = 9, 12, 14
PENDING_SIMO, PENDING_BANKA, PENDING_VALIDATION = 10, 13, 14

MISSING = "Fecho Não Creditado_aguarda tratamento da SIMO"
DUPLICATED = "Períodos duplicados_analisar individualmente"


def _fecho(pos_id: str, periodo: int, total: str, ops: int = 1) -> SimoClosing:
    return SimoClosing(pos_id, periodo, DIA, ops, Decimal(total))


def _credito(*montantes: str) -> BankaCredit:
    movimentos = [BankaMovement(DIA, Decimal(m), "P24-Fecho TPA") for m in montantes]
    total = sum((m.amount for m in movimentos), Decimal(0))
    return BankaCredit(total, DIA, "P24-Fecho TPA", movimentos)


def _workbook() -> Any:
    pos_ids = ["200001", "200002", "200003", "200004", "200005", "200006", "200007"]
    pos_list = {p: PosInfo(f"Comerciante {p}", f"ACC{p}", ClosingType.D) for p in pos_ids}
    closings = [
        _fecho("200001", 101, "100.00"),  # confere
        _fecho("200002", 102, "200.00"),  # incorrecto: Banka 190
        _fecho("200003", 103, "300.00"),  # não creditado
        _fecho("200004", 104, "50.00", ops=1),  # duplicado, por tratar
        _fecho("200004", 104, "70.00", ops=2),
        _fecho("200005", 105, "40.00", ops=1),  # duplicado, já regularizado
        _fecho("200005", 105, "60.00", ops=2),
        _fecho("200006", 106, "80.00"),  # um fecho, dois movimentos que não batem
        _fecho("200007", 107, "0.00"),  # zerado
    ]
    credits = {
        "200001101": _credito("100.00"),
        "200002102": _credito("190.00"),
        "200004104": _credito("50.00", "70.00"),
        "200005105": _credito("40.00", "60.00"),
        "200006106": _credito("30.00", "60.00"),
    }
    result = reconcile(pos_list, closings, credits)

    execution = SimpleNamespace(
        summary=result.summary.to_json_dict(),
        period_start=result.period_start,
        period_end=result.period_end,
    )
    cases = [
        SimpleNamespace(
            **asdict(case),
            status="resolved" if case.pos_id == "200005" else "pending",
            e_ticket=None,
            resolved_at=None,
        )
        for case in result.cases
    ]
    return load_workbook(BytesIO(build_workbook(execution, result.details, cases)))


@pytest.fixture(scope="module")
def workbook() -> Any:
    return _workbook()


def _row(sheet: Worksheet, row: int, columns: int) -> list[Any]:
    return [sheet.cell(row=row, column=2 + offset).value for offset in range(columns)]


def _data_rows(sheet: Worksheet) -> list[tuple[Any, ...]]:
    return [
        row
        for row in sheet.iter_rows(min_row=3, values_only=True)
        if any(value is not None for value in row)
    ]


def _column_sum(rows: list[tuple[Any, ...]], column: int) -> float:
    """Soma só os números — «n.a» é a célula que de propósito não entra na soma."""
    return sum(row[column - 1] for row in rows if isinstance(row[column - 1], int | float))


# ─── Cada folha ──────────────────────────────────────────────────────────────


def test_resumo_tem_uma_linha_por_causa_como_a_execucao(workbook: Any) -> None:
    """Um período duplicado não é um crédito incorrecto — não entra nessa linha."""
    resumo = workbook["Resumo"]

    assert _row(resumo, 7, 5) == pytest.approx(
        ["Fecho creditado incorrectamente", 1, 200, 190, -10]
    )
    assert _row(resumo, 8, 5) == pytest.approx([MISSING, 1, 300, 0, -300])
    # Duplicados: 2 + 2 fechos em chaves com vários fechos, 1 com vários movimentos.
    assert _row(resumo, 9, 5) == pytest.approx([DUPLICATED, 5, 300, 310, 10])
    assert _row(resumo, 10, 5) == pytest.approx(["Crédito Confere", 1, 100, 100, 0])
    assert _row(resumo, 11, 5) == pytest.approx(["Total", 8, 900, 600, -300])


def test_resumo_de_pendentes_conta_fechos_e_nao_duplica_os_duplicados(workbook: Any) -> None:
    """Um caso de período duplicado junta vários fechos — conta cada fecho uma vez."""
    resumo = workbook["Resumo"]

    assert resumo["B15"].value == "Total Casos Pendentes na SIMO"
    assert _row(resumo, 19, 3) == pytest.approx(["Fecho Regularizado", 2, 100])
    assert _row(resumo, 20, 3) == pytest.approx(["Fecho creditado incorrectamente", 1, 200])
    assert _row(resumo, 21, 3) == pytest.approx([MISSING, 1, 300])
    # O 200005 já foi regularizado: ficam os dois fechos do 200004 e o do 200006.
    assert _row(resumo, 22, 3) == pytest.approx([DUPLICATED, 3, 200])
    assert _row(resumo, 23, 3) == pytest.approx(["Total", 7, 800])


def test_pendentes_so_trazem_o_que_falta_tratar_com_a_causa_certa(workbook: Any) -> None:
    linhas = _data_rows(workbook["Total Casos Pendentes na SIMO"])

    assert [(row[1], row[PENDING_VALIDATION - 1]) for row in linhas] == [
        ("200002", "Fecho creditado incorrectamente"),
        ("200003", MISSING),
        ("200004", DUPLICATED),
        ("200004", DUPLICATED),
        ("200006", DUPLICATED),
    ]


def test_credito_de_chave_com_varios_fechos_so_vai_na_primeira_linha(workbook: Any) -> None:
    """Repetido em cada fecho, o crédito da chave somava a dobrar — o erro do VLOOKUP."""
    detalhes = [r for r in _data_rows(workbook["Detalhes Validacao"]) if r[1] == "200004"]
    pendentes = [
        r for r in _data_rows(workbook["Total Casos Pendentes na SIMO"]) if r[1] == "200004"
    ]

    assert [r[DETAILS_BANKA - 1] for r in detalhes] == [120, "n.a"]
    assert [r[PENDING_BANKA - 1] for r in pendentes] == [120, "n.a"]


# ─── As folhas fecham entre si ───────────────────────────────────────────────


def test_detalhe_soma_o_mesmo_que_o_total_do_resumo(workbook: Any) -> None:
    resumo = workbook["Resumo"]
    detalhes = _data_rows(workbook["Detalhes Validacao"])

    assert _column_sum(detalhes, DETAILS_SIMO) == pytest.approx(resumo["D11"].value)
    assert _column_sum(detalhes, DETAILS_BANKA) == pytest.approx(resumo["E11"].value)


def test_detalhe_conta_por_causa_o_mesmo_que_o_resumo(workbook: Any) -> None:
    resumo = workbook["Resumo"]
    detalhes = _data_rows(workbook["Detalhes Validacao"])

    for row in range(7, 11):
        label = resumo.cell(row=row, column=2).value
        assert (
            sum(1 for r in detalhes if r[DETAILS_VALIDATION - 1] == label)
            == resumo.cell(row=row, column=3).value
        )


def test_pendentes_fecham_com_as_linhas_por_tratar_do_resumo(workbook: Any) -> None:
    resumo = workbook["Resumo"]
    pendentes = _data_rows(workbook["Total Casos Pendentes na SIMO"])

    for row in range(20, 23):
        label = resumo.cell(row=row, column=2).value
        da_causa = [r for r in pendentes if r[PENDING_VALIDATION - 1] == label]
        assert len(da_causa) == resumo.cell(row=row, column=3).value
        assert _column_sum(da_causa, PENDING_SIMO) == pytest.approx(
            resumo.cell(row=row, column=4).value
        )


def test_regularizados_mais_pendentes_sao_todos_os_que_nao_conferem(workbook: Any) -> None:
    resumo = workbook["Resumo"]

    nao_conferem = sum(resumo.cell(row=row, column=3).value for row in range(7, 10))
    montante = sum(resumo.cell(row=row, column=4).value for row in range(7, 10))
    assert resumo["C23"].value == nao_conferem
    assert resumo["D23"].value == pytest.approx(montante)
