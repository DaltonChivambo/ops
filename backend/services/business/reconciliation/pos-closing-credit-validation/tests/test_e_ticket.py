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
    ("raw", "esperado"),
    [
        ("INC-4210", "INC-4210"),
        ("  SIMO/2026.0913_7  ", "SIMO/2026.0913_7"),
        ("1234", "1234"),
        ("", None),
        ("   ", None),
        (None, None),
    ],
)
def test_referencias_validas_guardam_se_aparadas_e_vazio_apaga(raw, esperado) -> None:
    assert normalize_e_ticket(raw) == esperado


@pytest.mark.parametrize(
    "raw",
    [
        "=HYPERLINK(\"http://x\",\"abrir\")",  # fórmula no Excel
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
def test_o_que_nao_tem_forma_de_referencia_e_recusado(raw) -> None:
    with pytest.raises(InvalidETicketError):
        normalize_e_ticket(raw)


def test_limite_de_tamanho() -> None:
    assert normalize_e_ticket("A" * MAX_E_TICKET_LENGTH) == "A" * MAX_E_TICKET_LENGTH
    with pytest.raises(InvalidETicketError):
        normalize_e_ticket("A" * (MAX_E_TICKET_LENGTH + 1))


def test_so_texto_e_aceite() -> None:
    with pytest.raises(InvalidETicketError):
        normalize_e_ticket(4210)


# ─── Rota ────────────────────────────────────────────────────────────────────


def test_e_ticket_invalido_e_regra_de_negocio_e_nao_muda_o_caso(client, service) -> None:
    antes = service.cases[0].status

    resposta = client.patch(
        f"{BASE}/casos/{CASE_ID}", json={"status": "resolved", "eTicket": "=1+1"}
    )

    assert resposta.status_code == 422
    erro = resposta.json()["error"]
    assert erro["code"] == "business_rule"
    assert "e-Ticket" in erro["message"]
    # Recusado o e-Ticket, o estado que vinha no mesmo pedido também não entra.
    assert service.cases[0].status == antes


# ─── Relatório ───────────────────────────────────────────────────────────────


def test_texto_comecado_por_igual_fica_texto_no_excel() -> None:
    sheet = Workbook().active

    _write_row(sheet, 1, ['=HYPERLINK("http://x","abrir")', "INC-4210", 12.5])

    formula, referencia, numero = (sheet.cell(row=1, column=2 + i) for i in range(3))
    assert formula.data_type == "s"
    assert formula.value == '=HYPERLINK("http://x","abrir")'
    assert referencia.data_type == "s"
    assert numero.data_type == "n"
