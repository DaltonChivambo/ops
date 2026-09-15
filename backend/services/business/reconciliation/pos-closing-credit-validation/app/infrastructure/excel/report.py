"""Geração do relatório FECHO_POS_DOP (openpyxl).

Porte de `infrastructure/report.py` do MozaOps v1. Fiel ao template do
Departamento de Meios de Pagamento e Canais (DOP). O layout segue o
ficheiro-modelo `FECHO_POS_DOP 21 a 28 de Junho-2026.xlsx`:

  · Todas as folhas de dados começam na coluna B (a coluna A fica vazia).
  · Resumo ....................... título em B3, dois blocos (validação e casos).
  · Detalhes Validacao .......... cabeçalho na linha 2, dados a partir da 3.
  · Total Casos Pendentes na SIMO cabeçalho na linha 2, só o que falta tratar.

São só estas três. O template do DOP trazia ainda o dump em bruto do Banka e a
folha «SQL» com a query de extracção — ambas saíram por não terem uso nenhum a
jusante: quem lê o relatório quer o apuramento, não a matéria-prima nem a forma
de a obter.

Todo o texto destas folhas é **conteúdo** — logo, em português.
"""

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from io import BytesIO
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from app.domain.vocabulary import CaseType, ClosingType, Validation

MOZA_RED = "FFC00000"
LIGHT_GREY = "FFF2F2F2"

MONEY_FORMAT = "#,##0.00"
# Formato «contabilístico» do template para os montantes de detalhe.
ACCOUNTING_FORMAT = r'_-* #,##0.00_-;\-* #,##0.00_-;_-* "-"??_-;_-@_-'

# Diferenças: o sinal é sempre explícito, `+` incluído. Numa diferença o sinal é a
# informação — o Banka creditou a mais ou a menos são problemas opostos —, e sem o
# `+` um valor positivo lê-se como um montante qualquer. As secções do formato são
# positivo;negativo;zero(;texto): o zero fica sem sinal, e a variante contabilística
# mantém o alinhamento do template na folha de detalhe.
SIGNED_MONEY_FORMAT = "+#,##0.00;-#,##0.00;#,##0.00"
SIGNED_ACCOUNTING_FORMAT = r'_-* +#,##0.00_-;\-* #,##0.00_-;_-* "-"??_-;_-@_-'
DATE_FORMAT = "dd/mm/yyyy"
NOT_APPLICABLE = "n.a"

# As folhas de dados do template deixam a coluna A vazia e começam em B.
FIRST_COLUMN = 2

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

VALIDATION_LABELS = {
    Validation.MATCH: "Crédito Confere",
    Validation.MISMATCH: "Fecho creditado incorrectamente",
    Validation.MISSING: "Fecho Não Creditado_aguarda tratamento da SIMO",
    Validation.ZERO: "Fecho zerado (sem movimento)",
    Validation.DUPLICATED: "Períodos duplicados_analisar individualmente",
}

CLOSING_TYPE_LABELS = {
    ClosingType.D: "D",
    ClosingType.D_PLUS_1: "D+1",
    ClosingType.NA: NOT_APPLICABLE,
}

DETAILS_HEADERS = [
    "POS ID",
    "Comerciante",
    "Número de Conta",
    "Período POS",
    "POS ID vs. Período",
    "Data Fecho \nSIMO",
    "Nº Operaç.",
    "Total Fecho \nSIMO",
    "Descritivo Fecho",
    "Data Crédito BANKA",
    "TOTAL FECHO \nBANKA",
    "TIPO Fecho",
    "Validação",
    "Diferença Apurada",
    "e-Ticket",
    "Data Reg.",
]

CASES_HEADERS = [
    "POS ID",
    "Balcão",
    "Unidade Negócio",
    "Comerciante",
    "Número de Conta",
    "Período POS",
    "Data Fecho \nSIMO",
    "Nº Operaç.",
    "Total Fecho \nSIMO",
    "TIPO Fecho",
    "Descritivo Fecho",
    "TOTAL FECHO \nBANKA",
    "Validação",
    "Data Reg.",
]

_HEADER_FILL = PatternFill("solid", fgColor=MOZA_RED)
_HEADER_FONT = Font(bold=True, color="FFFFFFFF")
_HEADER_ALIGN = Alignment(vertical="center", horizontal="center", wrap_text=True)
_THIN = Side(style="thin")
_HEADER_BORDER = Border(top=_THIN, bottom=_THIN, left=_THIN, right=_THIN)
_TOTAL_FILL = PatternFill("solid", fgColor=LIGHT_GREY)


def build_workbook(execution: Any, details: Sequence[Any], cases: list[Any]) -> bytes:
    workbook = Workbook()
    # O Workbook() nasce com uma folha vazia que não queremos; as três folhas do
    # relatório são criadas a seguir. O `active` é opcional no tipo, nunca na
    # prática — num livro acabado de criar há sempre uma.
    blank = workbook.active
    if blank is not None:
        workbook.remove(blank)

    _add_summary_sheet(workbook, execution, details, cases)
    _add_details_sheet(workbook, details, cases)
    _add_pending_cases_sheet(workbook, details, cases)

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _add_summary_sheet(
    workbook: Workbook, execution: Any, details: Sequence[Any], cases: list[Any]
) -> None:
    sheet = workbook.create_sheet("Resumo")
    summary = execution.summary or {}

    sheet["B3"] = _summary_title(execution.period_start, execution.period_end)
    sheet["B3"].font = Font(bold=True, size=13)

    _write_header(
        sheet,
        6,
        [
            "Descrição",
            "N° Fechos",
            "Montante de Fecho's Portal SIMO",
            "Montante de Fechos Creditados Banka",
            "Total (diferença apurada)",
        ],
    )

    # Uma linha por causa, pelas mesmas quatro categorias que a execução mostra no
    # ecrã: um período duplicado é ambiguidade por desfazer, não um crédito errado,
    # e juntá-lo aos incorrectos punha no Excel incorrectos que a execução não tem.
    #
    # Do lado do Banka, os duplicados levam o que foi creditado nessas chaves: o
    # crédito existe, só não se pode conferir por soma. Os não creditados são os
    # únicos sem contrapartida no Banka.
    validation_rows = [
        (Validation.MISMATCH, "mismatchCount", "simoAmountMismatched", "bankaAmountMismatched"),
        (Validation.MISSING, "missingCount", "simoAmountMissing", None),
        (
            Validation.DUPLICATED,
            "duplicatedPeriods",
            "simoAmountDuplicated",
            "bankaAmountDuplicated",
        ),
        (Validation.MATCH, "matched", "simoAmountMatched", "bankaAmountMatched"),
    ]
    first_row = 7
    total_count = 0
    total_simo = total_banka = Decimal(0)
    for offset, (validation, count_key, simo_key, banka_key) in enumerate(validation_rows):
        count = summary.get(count_key, 0)
        simo = _amount(summary.get(simo_key))
        banka = _amount(summary.get(banka_key)) if banka_key else Decimal(0)
        _write_row(
            sheet,
            first_row + offset,
            [VALIDATION_LABELS[validation], count, simo, banka, banka - simo],
        )
        total_count += count
        total_simo += simo
        total_banka += banka
    total_row = first_row + len(validation_rows)
    _write_row(
        sheet,
        total_row,
        ["Total", total_count, total_simo, total_banka, total_banka - total_simo],
        total=True,
    )

    title_row = total_row + 4
    sheet.merge_cells(f"B{title_row}:D{title_row}")
    sheet[f"B{title_row}"] = "Total Casos Pendentes na SIMO"
    sheet[f"B{title_row}"].font = Font(bold=True, size=12)

    header_row = title_row + 3
    _write_header(sheet, header_row, ["Descrição", "N° Fechos", "Montante de Fecho's"])

    # Conta-se fecho a fecho, a partir dos detalhes, e não caso a caso: um caso de
    # período duplicado junta vários fechos, e a folha «Total Casos Pendentes na
    # SIMO» lista-os um por linha. Todo o fecho que não confere tem caso, por isso
    # o Total deste bloco fecha com as três causas do bloco de cima, e as linhas por
    # tratar fecham com a folha de pendentes. Não se usa o `summary` aqui: é uma
    # fotografia da execução e não sabe o que já foi regularizado.
    pending_causes = [Validation.MISMATCH, Validation.MISSING, Validation.DUPLICATED]
    counts: dict[str, int] = {"resolved": 0, **dict.fromkeys(pending_causes, 0)}
    amounts: dict[str, Decimal] = {
        "resolved": Decimal(0),
        **dict.fromkeys(pending_causes, Decimal(0)),
    }
    case_by_key = {case.key: case for case in cases}
    for detail in details:
        case = case_by_key.get(detail.key)
        if case is None:
            continue
        bucket = "resolved" if case.status == "resolved" else detail.validation
        counts[bucket] += 1
        amounts[bucket] += detail.simo_closing_total

    block_rows = [("Fecho Regularizado", "resolved")] + [
        (VALIDATION_LABELS[cause], cause) for cause in pending_causes
    ]
    for offset, (label, bucket) in enumerate(block_rows, start=1):
        _write_row(sheet, header_row + offset, [label, counts[bucket], amounts[bucket]])
    block_total_row = header_row + len(block_rows) + 1
    _write_row(
        sheet,
        block_total_row,
        ["Total", sum(counts.values()), sum(amounts.values(), Decimal(0))],
        total=True,
    )

    _set_widths(sheet, [48, 12, 32, 34, 26])
    _set_format(sheet, ["D", "E"], MONEY_FORMAT, rows=range(first_row, total_row + 1))
    # F é «Total (diferença apurada)» — leva sinal.
    _set_format(sheet, ["F"], SIGNED_MONEY_FORMAT, rows=range(first_row, total_row + 1))
    _set_format(sheet, ["D"], MONEY_FORMAT, rows=range(header_row + 1, block_total_row + 1))


def _add_details_sheet(workbook: Workbook, details: Sequence[Any], cases: list[Any]) -> None:
    sheet = workbook.create_sheet("Detalhes Validacao")
    _write_header(sheet, 2, DETAILS_HEADERS)

    # e-Ticket e Data Reg. são colunas do modelo, preenchidas quando a chave tem
    # um caso em tratamento — vazias nos fechos que conferem.
    case_by_key = {case.key: case for case in cases}
    # O crédito do Banka é da chave: numa chave com vários fechos vai só na primeira
    # linha, pela mesma razão da folha de pendentes — repeti-lo inflacionava a soma
    # da coluna, que tem de dar o que o Banka creditou.
    credited_keys: set[str] = set()
    row_number = 3
    for detail in details:
        case = case_by_key.get(detail.key)
        first_of_key = detail.key not in credited_keys
        credited_keys.add(detail.key)
        banka_total = detail.banka_closing_total if detail.banka_closing_total is not None else 0
        _write_row(
            sheet,
            row_number,
            [
                detail.pos_id,
                detail.merchant,
                detail.account_number,
                detail.period,
                detail.key,
                detail.simo_closing_date,
                detail.operation_number,
                detail.simo_closing_total,
                detail.closing_description or NOT_APPLICABLE,
                detail.banka_credit_date or NOT_APPLICABLE,
                banka_total if first_of_key else NOT_APPLICABLE,
                CLOSING_TYPE_LABELS.get(detail.closing_type, NOT_APPLICABLE),
                VALIDATION_LABELS.get(detail.validation, detail.validation),
                detail.difference if detail.difference is not None else NOT_APPLICABLE,
                (case.e_ticket if case else None) or "",
                (case.resolved_at if case else None) or "",
            ],
        )
        row_number += 1

    _set_widths(sheet, [10, 32, 16, 12, 18, 14, 10, 18, 34, 16, 18, 10, 38, 16, 12, 12])
    # I é «Total Fecho SIMO»; O é «Diferença Apurada» — só esta leva sinal.
    _set_format(sheet, ["I"], ACCOUNTING_FORMAT, rows=range(3, row_number))
    _set_format(sheet, ["O"], SIGNED_ACCOUNTING_FORMAT, rows=range(3, row_number))
    _set_format(sheet, ["L"], MONEY_FORMAT, rows=range(3, row_number))
    _set_format(sheet, ["G", "K", "Q"], DATE_FORMAT, rows=range(3, row_number))
    sheet.freeze_panes = "A3"


def _add_pending_cases_sheet(workbook: Workbook, details: Sequence[Any], cases: list[Any]) -> None:
    """A lista do que fica por tratar — o que se leva à SIMO.

    Entram os três problemas que exigem acção, e só enquanto não estiverem
    tratados: creditado incorrectamente, não creditado e períodos duplicados. Um
    caso regularizado sai daqui (o Resumo é que o contabiliza) — os duplicados
    também têm caso, mas continuam a vir dos detalhes, um por fecho, porque é
    fecho a fecho que se desfaz a duplicação; o caso só decide se a chave ainda
    entra ou já saiu (foi regularizada).

    Cada linha leva o rótulo da sua causa, pela mesma ordem do Resumo — os
    duplicados como «Períodos duplicados», e não como incorrectos, para o Excel
    dizer o mesmo que a execução.
    """
    sheet = workbook.create_sheet("Total Casos Pendentes na SIMO")
    _write_header(sheet, 2, CASES_HEADERS)

    detail_by_key: dict[str, Any] = {}
    for detail in details:
        detail_by_key.setdefault(detail.key, detail)

    row_number = 3
    # Incorrectos primeiro, depois não creditados: dinheiro errado antes de dinheiro
    # em falta. Um caso regularizado já não está pendente na SIMO.
    for kind in (CaseType.MISMATCH, CaseType.MISSING):
        for case in (c for c in cases if c.type == kind and c.status != "resolved"):
            detail = detail_by_key.get(case.key)
            _write_row(
                sheet,
                row_number,
                [
                    case.pos_id,
                    NOT_APPLICABLE,  # Balcão (não vem nos ficheiros de entrada)
                    NOT_APPLICABLE,  # Unidade Negócio (idem)
                    case.merchant,
                    case.account_number,
                    case.period,
                    detail.simo_closing_date if detail else NOT_APPLICABLE,
                    detail.operation_number if detail else NOT_APPLICABLE,
                    case.simo_amount,
                    CLOSING_TYPE_LABELS.get(detail.closing_type, NOT_APPLICABLE)
                    if detail
                    else NOT_APPLICABLE,
                    (detail.closing_description if detail else None) or NOT_APPLICABLE,
                    case.banka_amount,
                    # `missing`/`mismatch` são os mesmos valores nos dois enums:
                    # o caso herda o rótulo da validação que lhe deu origem.
                    VALIDATION_LABELS[Validation(kind)],
                    case.resolved_at or NOT_APPLICABLE,
                ],
            )
            row_number += 1

    # Duplicados: um por fecho, com o valor do próprio fecho. O crédito do Banka é
    # da chave inteira (lá os movimentos também vêm duplicados), por isso vai só na
    # primeira linha de cada chave — repeti-lo em todas inflacionaria a coluna, que
    # é exactamente o erro do VLOOKUP manual que esta automação veio corrigir.
    #
    # Cada chave duplicada tem um caso próprio (um só, o `_build_cases` já
    # colapsa os vários fechos) — regularizá-lo tira a chave inteira daqui,
    # tal como um caso de incorrecto/não-creditado regularizado.
    duplicated_cases = {c.key: c for c in cases if c.type == CaseType.DUPLICATED}
    credited_keys: set[str] = set()
    for detail in (d for d in details if d.validation == "duplicated"):
        case = duplicated_cases.get(detail.key)
        if case is not None and case.status == "resolved":
            continue
        first_of_key = detail.key not in credited_keys
        credited_keys.add(detail.key)
        _write_row(
            sheet,
            row_number,
            [
                detail.pos_id,
                NOT_APPLICABLE,
                NOT_APPLICABLE,
                detail.merchant,
                detail.account_number,
                detail.period,
                detail.simo_closing_date,
                detail.operation_number,
                detail.simo_closing_total,
                CLOSING_TYPE_LABELS.get(detail.closing_type, NOT_APPLICABLE),
                detail.closing_description or NOT_APPLICABLE,
                detail.banka_closing_total
                if first_of_key and detail.banka_closing_total is not None
                else NOT_APPLICABLE,
                VALIDATION_LABELS[Validation.DUPLICATED],
                NOT_APPLICABLE,
            ],
        )
        row_number += 1

    # Colunas (com a A vazia): G=Período POS, H=Data Fecho, J=Total SIMO,
    # M=Total Banka, O=Data Reg. — não deslocar os formatos por causa da A.
    _set_widths(sheet, [10, 8, 18, 32, 16, 12, 14, 10, 18, 10, 34, 18, 42, 12])
    _set_format(sheet, ["J", "M"], MONEY_FORMAT, rows=range(3, row_number))
    _set_format(sheet, ["H", "O"], DATE_FORMAT, rows=range(3, row_number))
    sheet.freeze_panes = "A3"


def _summary_title(start: Any, end: Any) -> str:
    start = _excel_value(start)
    end = _excel_value(end)
    if start.month == end.month:
        span = f"{start.day}  a  {end.day} de {MONTHS_PT[end.month - 1]}  {end.year}"
    else:
        span = (
            f"{start.day} de {MONTHS_PT[start.month - 1]}  a  "
            f"{end.day} de {MONTHS_PT[end.month - 1]}  {end.year}"
        )
    return f"Validação de crédito de Fechos ({span})"


def _write_header(sheet: Worksheet, row: int, values: list[str]) -> None:
    for offset, value in enumerate(values):
        cell = sheet.cell(row=row, column=FIRST_COLUMN + offset, value=value)
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.alignment = _HEADER_ALIGN
        cell.border = _HEADER_BORDER


def _write_row(sheet: Worksheet, row: int, values: list[Any], *, total: bool = False) -> None:
    for offset, value in enumerate(values):
        cell = sheet.cell(row=row, column=FIRST_COLUMN + offset, value=_excel_value(value))
        if total:
            cell.font = Font(bold=True)
            cell.fill = _TOTAL_FILL


def _excel_value(value: Any) -> Any:
    """O Excel não aceita datas com fuso horário e a BD pode devolver `datetime`.

    As colunas de data guardam só a data (`Date`), logo só a data interessa —
    descarta-se a hora se por acaso vier um `datetime`.
    """
    if isinstance(value, datetime):
        return value.date()
    return value


def _set_widths(sheet: Worksheet, widths: list[int]) -> None:
    sheet.column_dimensions["A"].width = 2.5
    for offset, width in enumerate(widths):
        sheet.column_dimensions[get_column_letter(FIRST_COLUMN + offset)].width = width


def _set_format(sheet: Worksheet, columns: list[str], number_format: str, rows: range) -> None:
    for column in columns:
        for row in rows:
            sheet[f"{column}{row}"].number_format = number_format


def _amount(value: Any) -> Decimal:
    return Decimal(str(value or 0))
