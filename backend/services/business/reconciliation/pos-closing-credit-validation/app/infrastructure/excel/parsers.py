"""Adaptador de leitura dos três ficheiros de entrada (openpyxl).

Porte de `infrastructure/parsers.py` do MozaOps v1. Camada de infraestrutura:
é a única parte do serviço que sabe que os dados vêm de Excel. Produz as
estruturas de `domain/models.py` e nada mais.

Cada ficheiro é validado pelos cabeçalhos esperados ANTES de ser parseado — é
isso que também apanha um ficheiro carregado no campo errado.

As posições das colunas variam entre exports — **nos três ficheiros** —, por
isso todos resolvem as colunas pelo NOME do cabeçalho. A SIMO usava índices
fixos, contados a partir da coluna B: um export que começasse em C deslizava
tudo uma casa e lia «Id Comerciante» como POS Id (nenhum casava com a Lista) e
«Período POS» como data (4920 lido como serial do Excel dá 1913). Estruturas
(verificadas nos ficheiros reais):
  Lista POS ...... folha `Export`; colunas Merchant Id · POS Id · Nome Comerciante
                   · Nº Conta · Fecho Realtime (Sim/Não), em ordem/posição variável
  Fechos SIMO .... folha 1; Id Comerciante · POS Id · Período POS · Data Fecho
                   · Nº Operaç. · Total Fecho (pt), a começar em B ou em C
  Créditos Banka . folha `FECHO_POS`; DATA_SISTEMA · DESCRITIVO_MOV ·
                   VALOR_TRANSACAO, e N_DOCUMENTO para descartar movimentos
                   repetidos. As posições das colunas VARIAM entre exports
                   do MIS, por isso são resolvidas pelo NOME do cabeçalho e não
                   por índice fixo (ver `parse_banka_credits`). A chave «POS ID
                   vs. Período» é sempre derivada do DESCRITIVO_MOV.
"""

from collections.abc import Iterator
from itertools import chain, islice
from typing import IO, Any

from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet

from ...domain.errors import InvalidInputError
from ...domain.keys import key_from_description, normalize_pos_id
from ...domain.models import BankaCredit, BankaMovement, PosInfo, SimoClosing
from ...domain.vocabulary import SLOT_LABELS, ClosingType, UploadSlot
from .workbook import cell_date, cell_text, find_header_row, parse_number, validate_headers

# Cabeçalhos dos Fechos SIMO, por nome. O `Nº Operaç.` fica de fora da validação
# (`SIMO_REQUIRED`) porque um fecho sem ele continua a ser um fecho — conta zero
# operações e entra na mesma; os outros quatro, sem eles não há fecho nenhum.
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
) -> Worksheet:
    try:
        workbook = load_workbook(stream, read_only=True, data_only=True)
    # Apanha-se tudo de propósito: um ficheiro corrompido, um .xls antigo ou um
    # PDF renomeado levantam excepções diferentes do openpyxl, e para o operador
    # são todos o mesmo problema — o ficheiro não se lê.
    except Exception as error:
        raise InvalidInputError(
            f"Dados incompletos ou em formato inválido: não foi possível ler o ficheiro "
            f"«{filename}» no campo «{SLOT_LABELS[slot]}». Confirme que é um Excel (.xlsx) válido."
        ) from error

    if sheet_name and sheet_name in workbook.sheetnames:
        return workbook[sheet_name]
    if not workbook.sheetnames:
        raise _structure_error(slot, filename, [sheet_name or "folha de dados"])
    return workbook[workbook.sheetnames[0]]


def _header_and_rows(
    sheet: Worksheet,
    slot: UploadSlot,
    filename: str,
    anchor: str,
    expected: list[str],
) -> tuple[tuple[Any, ...], Iterator[tuple[Any, ...]]]:
    """Valida os cabeçalhos e devolve `(linha de cabeçalho, iterador de dados)`.

    A folha é percorrida uma única vez (`read_only`): só as primeiras linhas ficam
    em memória, para localizar o cabeçalho; o resto é consumido em streaming.
    """
    rows = sheet.iter_rows(values_only=True)
    head: list[tuple[Any, ...]] = []
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

    def _iter() -> Iterator[tuple[Any, ...]]:
        yield from head[header_index + 1 :]
        yield from rows

    return header, _iter()


def _value(row: tuple[Any, ...], index: int | None) -> Any:
    """Célula da coluna `index`, ou None se a coluna não existe nesta linha.

    O índice pode vir a None: é o que `_column_index` devolve quando não encontra
    o cabeçalho. Os cabeçalhos são validados antes de se chegar aqui, por isso na
    prática não acontece — mas a resposta certa é uma célula vazia, não o
    `TypeError` que `None < len(row)` levantava.
    """
    if index is None or index >= len(row):
        return None
    return row[index]


def _column_index(header: tuple[Any, ...], name: str) -> int | None:
    """Índice da 1ª coluna cujo cabeçalho começa por `name` (case-insensitive)."""
    target = name.lower()
    for index, cell in enumerate(header):
        if cell_text(cell).lower().startswith(target):
            return index
    return None


def _description_column(header: tuple[Any, ...], sample: list[tuple[Any, ...]]) -> int | None:
    """Escolhe a coluna DESCRITIVO_MOV que traz a chave.

    O export do MIS pode repetir o cabeçalho `DESCRITIVO_MOV` (uma versão truncada
    e a versão completa que contém «... - NNN»). Escolhe-se a coluna cujas linhas
    de amostra produzem uma chave válida; se nenhuma o fizer, a última (a completa
    costuma vir à direita).
    """
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
    """Lista de POS → `{posId: PosInfo}`. Fecho Realtime: Sim → D, Não → D+1.

    As colunas variam entre exports (o `ListaPOS_TOTAL` tem 48 colunas noutra
    ordem), por isso são resolvidas pelo NOME do cabeçalho. O POS Id é
    normalizado (sem zeros à esquerda) para casar com a SIMO e o Banka.
    """
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


def parse_banka_credits(stream: IO[bytes], filename: str) -> tuple[dict[str, BankaCredit], int]:
    """Créditos do Banka (MIS) agregados por chave «POS ID vs. Período».

    A chave é sempre derivada do DESCRITIVO_MOV — a coluna «POS ID vs. Período»
    não é usada (é considerada não-fiável e nem sempre existe no export). As
    posições das colunas variam entre exports, por isso são resolvidas pelo NOME
    do cabeçalho: DATA_SISTEMA, DESCRITIVO_MOV e VALOR_TRANSACAO.

    **Cada movimento entra uma vez só.** Um extracto montado a partir de dois
    que se sobrepõem traz o dia da junção duas vezes — visto num ficheiro de
    Agosto com o 19/08 inteiro repetido: 2 423 movimentos a dobrar, somados, e
    394 chaves a cair em «períodos repetidos» sem o serem. A identidade é o
    N_DOCUMENTO, único por movimento num export correcto; sem ele (coluna ausente
    ou célula vazia), a linha inteira — só colapsa o que é igual em tudo.

    Devolve os créditos e quantas linhas repetidas foram descartadas.
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
    # DESCRITIVO_MOV pode aparecer duplicado; escolhe-se pela amostra a que traz a chave.
    rows = iter(rows)
    sample = list(islice(rows, BANKA_SAMPLE_ROWS))
    desc_col = _description_column(header, sample)
    rows = chain(sample, rows)

    credits: dict[str, BankaCredit] = {}
    seen: set[object] = set()
    discarded = 0
    for row in rows:
        description = cell_text(_value(row, desc_col)) if desc_col is not None else ""
        key = key_from_description(description) if description else ""
        amount = parse_number(_value(row, amount_col)) if amount_col is not None else None
        if not key or amount is None:
            continue

        document = cell_text(_value(row, document_col))
        identity: object = ("doc", document) if document else ("row", row)
        if identity in seen:
            discarded += 1
            continue
        seen.add(identity)

        credit_date = cell_date(_value(row, date_col)) if date_col is not None else None
        movement = BankaMovement(date=credit_date, amount=amount, description=description or None)
        existing = credits.get(key)
        if existing:
            existing.amount += amount
            existing.movements.append(movement)
            # Uma chave pode ter movimentos em dias diferentes; a data de crédito
            # é a do primeiro movimento, não a da primeira linha que aparece no
            # ficheiro — o export do MIS não vem por ordem cronológica.
            if credit_date and (existing.credit_date is None or credit_date < existing.credit_date):
                existing.credit_date = credit_date
        else:
            credits[key] = BankaCredit(
                amount=amount,
                credit_date=credit_date,
                description=description or None,
                movements=[movement],
            )
    return credits, discarded
