"""Geração do relatório FECHO_POS_DOP (openpyxl)."""

import re
from collections.abc import Collection, Sequence
from datetime import datetime
from decimal import Decimal
from io import BytesIO
from typing import Any

from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from app.domain.vocabulary import CaseType, ClosingType, Validation

from . import styles

MONEY_FORMAT = "#,##0.00"
# Formato «contabilístico» do template para os montantes de detalhe.
ACCOUNTING_FORMAT = r'_-* #,##0.00_-;\-* #,##0.00_-;_-* "-"??_-;_-@_-'

# Diferenças com sinal explícito, `+` incluído: creditar a mais ou a menos são
# problemas opostos. Secções do formato: positivo;negativo;zero(;texto).
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
    Validation.DUPLICATED: "Períodos repetidos_analisar individualmente",
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

# Identificação e datas: cabeçalho de outra cor (ver `styles.MOZA_NAVY`).
DETAILS_IDENTITY_HEADERS = {
    "POS ID",
    "Comerciante",
    "Período POS",
    "Data Fecho \nSIMO",
    "Nº Operaç.",
    "Data Crédito BANKA",
    "Data Reg.",
}
# Colunas de valores curtos, centradas: período, chave, datas, nº de operação, tipo.
DETAILS_CENTERED = ("E", "F", "G", "H", "K", "M", "P", "Q")

# O período vem no fim do descritivo — «P24-Fecho TPA 0000263073 - 001».
_DESCRIPTION_PERIOD = re.compile(r"(\d+)\s*$")

# Na folha de pendentes, as mesmas famílias de colunas: identificação e datas a azul.
CASES_IDENTITY_HEADERS = {
    "POS ID",
    "Balcão",
    "Unidade Negócio",
    "Comerciante",
    "Período POS",
    "Data Fecho \nSIMO",
    "Nº Operaç.",
    "Data Reg.",
}
CASES_CENTERED = ("C", "D", "G", "H", "I", "K", "O")

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


def build_workbook(execution: Any, details: Sequence[Any], cases: list[Any]) -> bytes:
    workbook = Workbook()
    # O `Workbook()` nasce com uma folha vazia; as três do relatório vêm a seguir.
    blank = workbook.active
    if blank is not None:
        workbook.remove(blank)

    styles.document(workbook, _summary_title(execution.period_start, execution.period_end))
    _add_summary_sheet(workbook, execution, details, cases)
    _add_details_sheet(workbook, details, cases)
    _add_pending_cases_sheet(workbook, details, cases)

    buffer = BytesIO()
    workbook.save(buffer)
    # POS ID, conta e chave são dígitos guardados como texto (a conta tem zeros à
    # esquerda); sem isto o Excel marca cada célula com o triângulo verde.
    return styles.ignore_number_as_text(
        buffer.getvalue(),
        {
            "Detalhes Validacao": "B3:F1048576",
            "Total Casos Pendentes na SIMO": "B3:F1048576",
        },
    )


def _add_summary_sheet(
    workbook: Workbook, execution: Any, details: Sequence[Any], cases: list[Any]
) -> None:
    sheet = workbook.create_sheet("Resumo")
    summary = execution.summary or {}

    sheet.sheet_properties.tabColor = styles.MOZA_RED
    styles.cover(
        sheet,
        _summary_title(execution.period_start, execution.period_end),
        f"Departamento de Meios de Pagamento e Canais · gerado em {_generated_at(execution)}",
    )

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

    # Uma linha por causa, pelas quatro categorias do ecrã. Os duplicados levam o
    # que foi creditado nessas chaves; os não creditados são os únicos sem Banka.
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
        styles.summary_row(sheet, first_row + offset, 5)
        styles.state_cell(sheet.cell(row=first_row + offset, column=2), validation.value)
        total_count += count
        total_simo += simo
        total_banka += banka
    total_row = first_row + len(validation_rows)
    # Os repetidos numa linha própria, só com a contagem: o dinheiro deles já está
    # na linha do estado da chave.
    simo_duplicates = int(summary.get("duplicatesDiscarded", 0))
    if simo_duplicates:
        _write_row(
            sheet,
            total_row,
            [
                "Fechos repetidos na SIMO",
                simo_duplicates,
                NOT_APPLICABLE,
                NOT_APPLICABLE,
                NOT_APPLICABLE,
            ],
        )
        styles.summary_row(sheet, total_row, 5)
        styles.state_cell(sheet.cell(row=total_row, column=2), "repeated")
        for column in range(4, 7):
            sheet.cell(row=total_row, column=column).alignment = styles.RIGHT
        total_count += simo_duplicates
        total_row += 1
    _write_row(
        sheet,
        total_row,
        ["Total", total_count, total_simo, total_banka, total_banka - total_simo],
    )
    styles.summary_row(sheet, total_row, 5, total=True)

    title_row = total_row + 4
    sheet.merge_cells(f"B{title_row}:D{title_row}")
    sheet[f"B{title_row}"] = "Total Casos Pendentes na SIMO"
    styles.section_title(sheet, f"B{title_row}", "D")

    header_row = title_row + 3
    _write_header(sheet, header_row, ["Descrição", "N° Fechos", "Montante de Fecho's"])

    # Fecho a fecho a partir dos detalhes, e não caso a caso: um caso de período
    # duplicado junta vários fechos. Não se usa o `summary`, que não sabe o que já
    # foi regularizado.
    pending_causes = [Validation.MISMATCH, Validation.MISSING, Validation.DUPLICATED]
    counts: dict[str, int] = {"resolved": 0, **dict.fromkeys(pending_causes, 0)}
    amounts: dict[str, Decimal] = {
        "resolved": Decimal(0),
        **dict.fromkeys(pending_causes, Decimal(0)),
    }
    case_by_key = {case.key: case for case in cases}
    for detail in details:
        case = case_by_key.get(detail.key)
        if case is None or getattr(detail, "simo_duplicate", False):
            continue
        # Conciliado num caso ainda aberto conta como regularizado, não «confere».
        reconciled = detail.validation == Validation.MATCH
        bucket = "resolved" if case.status == "resolved" or reconciled else detail.validation
        counts[bucket] += 1
        amounts[bucket] += detail.simo_closing_total

    block_rows = [("Fecho Regularizado", "resolved")] + [
        (VALIDATION_LABELS[cause], cause) for cause in pending_causes
    ]
    for offset, (label, bucket) in enumerate(block_rows, start=1):
        _write_row(sheet, header_row + offset, [label, counts[bucket], amounts[bucket]])
        styles.summary_row(sheet, header_row + offset, 3)
        styles.state_cell(sheet.cell(row=header_row + offset, column=2), str(bucket))
    block_total_row = header_row + len(block_rows) + 1
    _write_row(
        sheet,
        block_total_row,
        ["Total", sum(counts.values()), sum(amounts.values(), Decimal(0))],
    )
    styles.summary_row(sheet, block_total_row, 3, total=True)

    # As linhas dos ficheiros e as repetidas. As da SIMO contam como fecho; as do
    # Banka vão para análise. As execuções antigas fundiam as do Banka numa só,
    # e guardaram-nas noutro campo.
    lines_title_row = block_total_row + 4
    sheet.merge_cells(f"B{lines_title_row}:D{lines_title_row}")
    sheet[f"B{lines_title_row}"] = "Linhas dos ficheiros"
    styles.section_title(sheet, f"B{lines_title_row}", "D")
    lines_header_row = lines_title_row + 2
    _write_header(sheet, lines_header_row, ["Descrição", "N° Linhas"])
    processed = int(summary.get("processed", 0))
    simo_repeated = int(summary.get("duplicatesDiscarded", 0))
    lines = [
        ("Fechos no ficheiro da SIMO", processed),
        ("Dos quais repetidos", simo_repeated),
    ]
    if "bankaDuplicatesDiscarded" in summary:
        lines.append(
            (
                "Movimentos repetidos no Banka, contados uma vez",
                int(summary["bankaDuplicatesDiscarded"]),
            )
        )
    else:
        lines.append(
            (
                "Créditos repetidos no Banka, enviados para análise",
                int(summary.get("bankaRepeatedMovements", 0)),
            )
        )
    for offset, (label, value) in enumerate(lines, start=1):
        _write_row(sheet, lines_header_row + offset, [label, value])
        styles.summary_row(sheet, lines_header_row + offset, 2)

    _set_widths(sheet, [48, 12, 32, 34, 26])
    _set_format(sheet, ["D", "E"], MONEY_FORMAT, rows=range(first_row, total_row + 1))
    # F é «Total (diferença apurada)» — leva sinal.
    _set_format(sheet, ["F"], SIGNED_MONEY_FORMAT, rows=range(first_row, total_row + 1))
    _set_format(sheet, ["D"], MONEY_FORMAT, rows=range(header_row + 1, block_total_row + 1))
    styles.printable(sheet)


def _add_details_sheet(workbook: Workbook, details: Sequence[Any], cases: list[Any]) -> None:
    sheet = workbook.create_sheet("Detalhes Validacao")
    _write_header(sheet, 2, DETAILS_HEADERS, identity=DETAILS_IDENTITY_HEADERS)

    # e-Ticket e Data Reg. preenchem-se quando a chave tem caso; senão «n.a».
    case_by_key = {case.key: case for case in cases}
    # O crédito é da chave: com vários fechos vai só na primeira linha, senão a
    # soma da coluna inflaciona.
    credited_keys: set[str] = set()
    row_number = 3
    # Período POS e chave marcados nas linhas duplicadas: a original e as cópias.
    marked: list[str] = []
    original_row = 3
    for detail in sorted(details, key=_details_order):
        case = case_by_key.get(detail.key)
        # A cópia vem logo a seguir à original: mesma validação, sem crédito repetido.
        copy = bool(getattr(detail, "simo_duplicate", False))
        if copy:
            marked.append(f"E{original_row}:F{row_number}")
        else:
            original_row = row_number
        confere = detail.validation == Validation.MATCH
        first_of_key = not copy and detail.key not in credited_keys
        if not copy:
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
                NOT_APPLICABLE if copy else detail.banka_credit_date or NOT_APPLICABLE,
                banka_total if first_of_key else NOT_APPLICABLE,
                CLOSING_TYPE_LABELS.get(detail.closing_type, NOT_APPLICABLE),
                VALIDATION_LABELS.get(detail.validation, detail.validation),
                detail.difference if detail.difference is not None else NOT_APPLICABLE,
                NOT_APPLICABLE if confere else (case.e_ticket if case else None) or "",
                NOT_APPLICABLE if confere else (case.resolved_at if case else None) or "",
            ],
        )
        row_number += 1

    _set_widths(sheet, [12, 34, 18, 14, 20, 16, 13, 18, 34, 17, 18, 13, 48, 18, 14, 13])
    _set_alignment(sheet, DETAILS_CENTERED, rows=range(3, row_number))

    # I é «Total Fecho SIMO»; O é «Diferença Apurada» — só esta leva sinal.
    _set_format(sheet, ["I"], ACCOUNTING_FORMAT, rows=range(3, row_number))
    _set_format(sheet, ["O"], SIGNED_ACCOUNTING_FORMAT, rows=range(3, row_number))
    _set_format(sheet, ["L"], MONEY_FORMAT, rows=range(3, row_number))
    _set_format(sheet, ["G", "K", "Q"], DATE_FORMAT, rows=range(3, row_number))
    styles.data_sheet(
        sheet,
        header=2,
        last_row=row_number - 1,
        columns=len(DETAILS_HEADERS),
        validation_column="N",
        difference_column="O",
        tab_color=styles.MUTED,
        marked=marked,
    )


def _add_pending_cases_sheet(workbook: Workbook, details: Sequence[Any], cases: list[Any]) -> None:
    """A lista do que fica por tratar — o que se leva à SIMO."""
    sheet = workbook.create_sheet("Total Casos Pendentes na SIMO")
    _write_header(sheet, 2, CASES_HEADERS, identity=CASES_IDENTITY_HEADERS)

    detail_by_key: dict[str, Any] = {}
    for detail in details:
        detail_by_key.setdefault(detail.key, detail)

    row_number = 3

    # Incorrectos, depois não creditados; um caso regularizado já não está pendente.
    # Dentro da causa, a ordem da folha de detalhes: POS a POS, pelo período.
    def case_order(case: Any) -> tuple[str, int, Any, int]:
        detail = detail_by_key.get(case.key)
        return _details_order(detail) if detail else (case.pos_id, case.period % 1000, "", 0)

    for kind in (CaseType.MISMATCH, CaseType.MISSING):
        pending = [c for c in cases if c.type == kind and c.status != "resolved"]
        for case in sorted(pending, key=case_order):
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
                    # `missing`/`mismatch` valem nos dois enums: o caso herda o rótulo.
                    VALIDATION_LABELS[Validation(kind)],
                    case.resolved_at or NOT_APPLICABLE,
                ],
            )
            row_number += 1

    # Um por fecho, com o valor do próprio fecho. O crédito é da chave, por isso
    # vai só na primeira linha. Cada chave duplicada tem um caso só, e regularizá-lo
    # tira a chave inteira daqui.
    duplicated_cases = {c.key: c for c in cases if c.type == CaseType.DUPLICATED}
    credited_keys: set[str] = set()
    duplicated = [
        d
        for d in details
        if d.validation == Validation.DUPLICATED and not getattr(d, "simo_duplicate", False)
    ]
    for detail in sorted(duplicated, key=_details_order):
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

    if row_number == 3:
        # Nada por tratar: diz-se, em vez de deixar só o cabeçalho.
        sheet.merge_cells(
            start_row=3,
            start_column=FIRST_COLUMN,
            end_row=3,
            end_column=1 + len(CASES_HEADERS),
        )
        sheet.cell(row=3, column=FIRST_COLUMN, value="Sem casos pendentes na SIMO.")
        styles.empty_message(sheet.cell(row=3, column=FIRST_COLUMN))

    # Colunas (com a A vazia): G=Período POS, H=Data Fecho, J=Total SIMO,
    # M=Total Banka, O=Data Reg.
    _set_widths(sheet, [12, 12, 18, 34, 18, 14, 16, 13, 18, 13, 34, 18, 48, 13])
    _set_format(sheet, ["J", "M"], MONEY_FORMAT, rows=range(3, row_number))
    _set_format(sheet, ["H", "O"], DATE_FORMAT, rows=range(3, row_number))
    _set_alignment(sheet, CASES_CENTERED, rows=range(3, row_number))
    styles.data_sheet(
        sheet,
        header=2,
        last_row=row_number - 1,
        columns=len(CASES_HEADERS),
        validation_column="N",
        difference_column=None,
        tab_color=styles.STATE_TONES["duplicated"][1],
    )


def _summary_title(start: Any, end: Any) -> str:
    start = _excel_value(start)
    end = _excel_value(end)
    if start.month == end.month:
        span = f"{start.day} a {end.day} de {MONTHS_PT[end.month - 1]} de {end.year}"
    else:
        span = (
            f"{start.day} de {MONTHS_PT[start.month - 1]} a "
            f"{end.day} de {MONTHS_PT[end.month - 1]} de {end.year}"
        )
    return f"Validação de crédito de Fechos ({span})"


def _write_header(
    sheet: Worksheet, row: int, values: list[str], *, identity: Collection[str] = ()
) -> None:
    for offset, value in enumerate(values):
        styles.header_cell(
            sheet.cell(row=row, column=FIRST_COLUMN + offset, value=value),
            identity=value in identity,
        )
    styles.header_row(sheet, row)


def _details_order(detail: Any) -> tuple[str, int, Any, int]:
    """POS a POS, e dentro de cada POS pelo período do descritivo, do mais antigo."""
    match = _DESCRIPTION_PERIOD.search(detail.closing_description or "")
    period = int(match.group(1)) if match else detail.period % 1000
    return (detail.pos_id, period, detail.simo_closing_date, detail.operation_number)


def _write_row(sheet: Worksheet, row: int, values: list[Any]) -> None:
    for offset, value in enumerate(values):
        cell = sheet.cell(row=row, column=FIRST_COLUMN + offset, value=_excel_value(value))
        # O openpyxl grava como fórmula qualquer texto começado por «=». Um
        # «=HYPERLINK(...)» vindo dos ficheiros corria no Excel de quem abrisse.
        if cell.data_type == "f":
            cell.data_type = "s"


def _generated_at(execution: Any) -> str:
    executed_at = getattr(execution, "executed_at", None)
    if isinstance(executed_at, datetime):
        return f"{executed_at:%d/%m/%Y às %H:%M}"
    return "—" if executed_at is None else str(executed_at)


def _excel_value(value: Any) -> Any:
    """O Excel não aceita datas com fuso horário e a BD pode devolver `datetime`."""
    if isinstance(value, datetime):
        return value.date()
    return value


def _set_widths(sheet: Worksheet, widths: list[int]) -> None:
    sheet.column_dimensions["A"].width = 2.5
    for offset, width in enumerate(widths):
        sheet.column_dimensions[get_column_letter(FIRST_COLUMN + offset)].width = width


def _set_alignment(sheet: Worksheet, columns: Sequence[str], rows: range) -> None:
    for column in columns:
        for row in rows:
            sheet[f"{column}{row}"].alignment = styles.CENTER


def _set_format(sheet: Worksheet, columns: list[str], number_format: str, rows: range) -> None:
    for column in columns:
        for row in rows:
            sheet[f"{column}{row}"].number_format = number_format


def _amount(value: Any) -> Decimal:
    return Decimal(str(value or 0))
