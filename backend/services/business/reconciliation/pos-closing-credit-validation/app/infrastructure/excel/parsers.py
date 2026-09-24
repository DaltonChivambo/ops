"""Adaptador de leitura dos três ficheiros de entrada (calamine)."""

from collections.abc import Iterator, Sequence
from itertools import chain, islice
from typing import IO, Any

from python_calamine import CalamineSheet, CalamineWorkbook

from ...domain.errors import InvalidInputError
from ...domain.keys import key_from_description, normalize_pos_id
from ...domain.models import BankaCredit, BankaMovement, PosInfo, SimoClosing
from ...domain.vocabulary import SLOT_LABELS, ClosingType, UploadSlot
from .workbook import cell_date, cell_text, find_header_row, parse_number, validate_headers

# Cabeçalhos dos Fechos SIMO, por nome. O `Nº Operaç.` fica fora de `SIMO_REQUIRED`:
# um fecho sem ele conta zero operações e entra na mesma.
SIMO_HEADERS = {
    "pos_id": "pos id",
    "period": "período pos",
    "closing_date": "data fecho",
    "operation_number": "nº operaç",
    "total": "total fecho",
}
SIMO_REQUIRED = ["id comerciante", "pos id", "período pos", "data fecho", "total fecho"]

HEADER_SEARCH_ROWS = 10
BANKA_SAMPLE_ROWS = 20  # linhas espreitadas para escolher a coluna DESCRITIVO_MOV certa


def _structure_error(slot: UploadSlot, filename: str, missing: list[str]) -> InvalidInputError:
    return InvalidInputError(
        f"Dados incompletos ou em formato inválido: o ficheiro «{filename}» no campo "
        f"«{SLOT_LABELS[slot]}» não tem as colunas esperadas ({', '.join(missing)}). "
        "Verifique se carregou o ficheiro correcto e volte a submeter."
    )


def _open_sheet(
    stream: IO[bytes], slot: UploadSlot, filename: str, sheet_name: str | None
) -> CalamineSheet:
    try:
        workbook = CalamineWorkbook.from_filelike(stream)
    # Corrompido, .xls antigo ou PDF renomeado levantam excepções diferentes, e
    # para o operador são o mesmo problema.
    except Exception as error:
        raise InvalidInputError(
            f"Dados incompletos ou em formato inválido: não foi possível ler o ficheiro "
            f"«{filename}» no campo «{SLOT_LABELS[slot]}». Confirme que é um Excel (.xlsx) válido."
        ) from error

    names = workbook.sheet_names
    if sheet_name and sheet_name in names:
        return workbook.get_sheet_by_name(sheet_name)
    if not names:
        raise _structure_error(slot, filename, [sheet_name or "folha de dados"])
    return workbook.get_sheet_by_name(names[0])


def _header_and_rows(
    sheet: CalamineSheet,
    slot: UploadSlot,
    filename: str,
    anchor: str,
    expected: list[str],
) -> tuple[Sequence[Any], Iterator[Sequence[Any]]]:
    """Valida os cabeçalhos e devolve `(linha de cabeçalho, iterador de dados)`."""
    rows = iter(sheet.to_python(skip_empty_area=False))
    head: list[Sequence[Any]] = []
    for row in rows:
        head.append(row)
        if len(head) >= HEADER_SEARCH_ROWS:
            break

    header_index = find_header_row(head, anchor)
    if header_index is None:
        raise _structure_error(slot, filename, [anchor])

    header = head[header_index]
    missing = validate_headers(header, expected)
    if missing:
        raise _structure_error(slot, filename, missing)

    def _iter() -> Iterator[Sequence[Any]]:
        yield from head[header_index + 1 :]
        yield from rows

    return header, _iter()


def _value(row: Sequence[Any], index: int | None) -> Any:
    """Célula da coluna `index`, ou None se a coluna não existe nesta linha."""
    if index is None or index >= len(row):
        return None
    return row[index]


def _column_index(header: Sequence[Any], name: str) -> int | None:
    """Índice da 1ª coluna cujo cabeçalho começa por `name` (case-insensitive)."""
    target = name.lower()
    for index, cell in enumerate(header):
        if cell_text(cell).lower().startswith(target):
            return index
    return None


def _description_column(header: Sequence[Any], sample: list[Sequence[Any]]) -> int | None:
    """Escolhe a coluna DESCRITIVO_MOV que traz a chave."""
    candidates = [
        index
        for index, cell in enumerate(header)
        if cell_text(cell).lower().startswith("descritivo")
    ]
    if len(candidates) <= 1:
        return candidates[0] if candidates else None
    for index in candidates:
        if any(key_from_description(cell_text(_value(row, index))) for row in sample):
            return index
    return candidates[-1]


def parse_pos_list(stream: IO[bytes], filename: str) -> dict[str, PosInfo]:
    """Lista de POS → `{posId: PosInfo}`. Fecho Realtime: Sim → D, Não → D+1."""
    sheet = _open_sheet(stream, UploadSlot.POS_LIST, filename, "Export")
    header, rows = _header_and_rows(
        sheet,
        UploadSlot.POS_LIST,
        filename,
        "merchant id",
        ["merchant id", "pos id", "nome comerciante", "nº conta", "fecho realtime"],
    )

    pos_id_col = _column_index(header, "pos id")
    merchant_col = _column_index(header, "nome comerciante")
    account_col = _column_index(header, "nº conta")
    realtime_col = _column_index(header, "fecho realtime")

    result: dict[str, PosInfo] = {}
    for row in rows:
        pos_id = normalize_pos_id(cell_text(_value(row, pos_id_col)))
        if not pos_id:
            continue
        realtime = cell_text(_value(row, realtime_col)).lower()
        result[pos_id] = PosInfo(
            merchant=cell_text(_value(row, merchant_col)),
            account_number=cell_text(_value(row, account_col)),
            closing_type=(
                ClosingType.D
                if realtime == "sim"
                else ClosingType.D_PLUS_1
                if realtime in ("não", "nao")
                else ClosingType.NA
            ),
        )
    return result


def parse_simo_closings(stream: IO[bytes], filename: str) -> list[SimoClosing]:
    """Fechos do Portal SIMO → lista de fechos válidos."""
    sheet = _open_sheet(stream, UploadSlot.SIMO_CLOSINGS, filename, None)
    header, rows = _header_and_rows(
        sheet,
        UploadSlot.SIMO_CLOSINGS,
        filename,
        "id comerciante",
        SIMO_REQUIRED,
    )
    column = {name: _column_index(header, title) for name, title in SIMO_HEADERS.items()}

    closings: list[SimoClosing] = []
    for row in rows:
        pos_id = normalize_pos_id(cell_text(_value(row, column["pos_id"])))
        period = parse_number(_value(row, column["period"]))
        total = parse_number(_value(row, column["total"]))
        closing_date = cell_date(_value(row, column["closing_date"]))
        if not pos_id or period is None or total is None or closing_date is None:
            continue
        operation = parse_number(_value(row, column["operation_number"]))
        closings.append(
            SimoClosing(
                pos_id=pos_id,
                period=int(period),
                closing_date=closing_date,
                operation_number=int(operation) if operation is not None else 0,
                total=total,
                row=tuple(cell_text(value) for value in row),
            )
        )
    return closings


def parse_banka_credits(
    stream: IO[bytes], filename: str
) -> tuple[dict[str, BankaCredit], dict[str, int]]:
    """Créditos do Banka (MIS) agregados por chave «POS ID vs. Período».

    Um movimento com N_DOCUMENTO repetido não se funde: pode ser o mesmo crédito
    exportado duas vezes ou um crédito em dobro, e só a análise o decide. Soma à
    chave como os outros, e devolve-se quantos havia em cada chave.
    """
    sheet = _open_sheet(stream, UploadSlot.BANKA_CREDITS, filename, "FECHO_POS")
    header, rows = _header_and_rows(
        sheet,
        UploadSlot.BANKA_CREDITS,
        filename,
        "data_sistema",
        ["data_sistema", "descritivo", "valor_transacao"],
    )

    date_col = _column_index(header, "data_sistema")
    amount_col = _column_index(header, "valor_transacao")
    document_col = _column_index(header, "n_documento")
    # DESCRITIVO_MOV pode vir duplicado; a amostra escolhe a que traz a chave.
    rows = iter(rows)
    sample = list(islice(rows, BANKA_SAMPLE_ROWS))
    desc_col = _description_column(header, sample)
    rows = chain(sample, rows)

    credits: dict[str, BankaCredit] = {}
    seen: set[object] = set()
    repeated: dict[str, int] = {}
    for row in rows:
        description = cell_text(_value(row, desc_col)) if desc_col is not None else ""
        key = key_from_description(description) if description else ""
        amount = parse_number(_value(row, amount_col)) if amount_col is not None else None
        if not key or amount is None:
            continue

        document = cell_text(_value(row, document_col))
        # Sem documento a identidade é a linha inteira, e o leitor entrega-a como lista.
        identity: object = ("doc", document) if document else ("row", tuple(row))
        if identity in seen:
            repeated[key] = repeated.get(key, 0) + 1
        seen.add(identity)

        credit_date = cell_date(_value(row, date_col)) if date_col is not None else None
        movement = BankaMovement(date=credit_date, amount=amount, description=description or None)
        existing = credits.get(key)
        if existing:
            existing.amount += amount
            existing.movements.append(movement)
            # A data de crédito é a do primeiro movimento, não a da primeira linha:
            # o export do MIS não vem por ordem cronológica.
            if credit_date and (existing.credit_date is None or credit_date < existing.credit_date):
                existing.credit_date = credit_date
        else:
            credits[key] = BankaCredit(
                amount=amount,
                credit_date=credit_date,
                description=description or None,
                movements=[movement],
            )
    return credits, repeated
