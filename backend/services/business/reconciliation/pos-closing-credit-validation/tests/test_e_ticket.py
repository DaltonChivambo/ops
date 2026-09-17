"""O e-Ticket é texto escrito à mão que acaba no Excel do departamento.

Três coisas a provar: só se guarda o que tem forma de referência, a recusa
chega ao operador em português pela rota, e nada do que se escreve no
relatório vira fórmula — venha do e-Ticket ou dos ficheiros carregados.
"""

import pytest
from openpyxl import Workbook

from app.domain.e_ticket import MAX_E_TICKET_LENGTH, normalize_e_ticket
from app.domain.errors import InvalidETicketError
from app.infrastructure.excel.report import _write_row
from tests.conftest import CASE_ID

BASE = "/pos/validacao-credito-fecho"


# ─── Domínio ─────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("INC-4210", "INC-4210"),
        ("  SIMO/2026.0913_7  ", "SIMO/2026.0913_7"),
        ("1234", "1234"),
        ("", None),
        ("   ", None),
        (None, None),
    ],
)
def test_valid_references_are_trimmed_and_empty_clears(raw, expected) -> None:
    assert normalize_e_ticket(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        '=HYPERLINK("http://x","abrir")',  # fórmula no Excel
        "+1+1",
        "-2",
        "@SUM(A1)",
        "INC 4210",  # espaço: duas referências que parecem iguais
        "INC\t4210",
        "<script>",
        "INC-4210;DROP",
        "ÇÃO-1",
    ],
)
def test_non_reference_shape_is_rejected(raw) -> None:
    with pytest.raises(InvalidETicketError):
        normalize_e_ticket(raw)


def test_length_limit() -> None:
    assert normalize_e_ticket("A" * MAX_E_TICKET_LENGTH) == "A" * MAX_E_TICKET_LENGTH
    with pytest.raises(InvalidETicketError):
        normalize_e_ticket("A" * (MAX_E_TICKET_LENGTH + 1))


def test_only_text_is_accepted() -> None:
    with pytest.raises(InvalidETicketError):
        normalize_e_ticket(4210)


# ─── Rota ────────────────────────────────────────────────────────────────────


def test_invalid_e_ticket_is_business_rule_and_leaves_case_unchanged(client, service) -> None:
    before = service.cases[0].status

    response = client.patch(
        f"{BASE}/casos/{CASE_ID}", json={"status": "resolved", "eTicket": "=1+1"}
    )

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "business_rule"
    assert "e-Ticket" in error["message"]
    # Recusado o e-Ticket, o estado que vinha no mesmo pedido também não entra.
    assert service.cases[0].status == before


# ─── Relatório ───────────────────────────────────────────────────────────────


def test_text_starting_with_equals_stays_text_in_excel() -> None:
    sheet = Workbook().active

    _write_row(sheet, 1, ['=HYPERLINK("http://x","abrir")', "INC-4210", 12.5])

    formula, reference, number = (sheet.cell(row=1, column=2 + i) for i in range(3))
    assert formula.data_type == "s"
    assert formula.value == '=HYPERLINK("http://x","abrir")'
    assert reference.data_type == "s"
    assert number.data_type == "n"
