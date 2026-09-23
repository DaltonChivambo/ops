"""Utilitários de leitura de Excel — porte de `shared/excel.py` do MozaOps v1."""

import re
from collections.abc import Iterable, Sequence
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

# Dias entre a epoch do Excel (1899-12-30) e a do Unix (1970-01-01).
EXCEL_EPOCH_OFFSET = 25569
SECONDS_PER_DAY = 86400

EXCEL_EPOCH = date(1899, 12, 30)
# Fora deste intervalo o número não é data, é um período ou um código. Guarda
# também o `datetime.fromtimestamp`, que com timestamp negativo falha no Windows.
MIN_DATE_SERIAL = (date(2000, 1, 1) - EXCEL_EPOCH).days
MAX_DATE_SERIAL = (date(2100, 1, 1) - EXCEL_EPOCH).days

_DDMMYYYY = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")
_PT_NUMBER = re.compile(r"^-?[\d.]+,\d+$")

Row = Sequence[Any]


def _excel_serial_to_date(serial: float) -> date:
    """Converte um serial de data do Excel (epoch 1899-12-30) para `date`."""
    timestamp = round((serial - EXCEL_EPOCH_OFFSET) * SECONDS_PER_DAY)
    return datetime.fromtimestamp(timestamp, tz=UTC).date()


def _ddmmyyyy_to_date(value: str) -> date | None:
    """Converte `dd/mm/yyyy` para `date`; devolve None se não reconhecer."""
    match = _DDMMYYYY.match(value.strip())
    if not match:
        return None
    day, month, year = (int(part) for part in match.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


def parse_number(value: Any) -> Decimal | None:
    """Interpreta um valor numérico de célula."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float, Decimal)):
        return Decimal(str(value))
    if not isinstance(value, str):
        return None

    raw = value.strip()
    if not raw:
        return None
    if _PT_NUMBER.match(raw):
        raw = raw.replace(".", "").replace(",", ".")
    try:
        return Decimal(raw)
    except InvalidOperation:
        return None


def cell_text(value: Any) -> str:
    """Extrai o valor de célula como string aparada ('' quando vazia)."""
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, float) and value.is_integer():
        # Um código numérico vem como 252524.0; queremos "252524".
        return str(int(value))
    return str(value).strip()


def cell_date(value: Any) -> date | None:
    """Data de célula: aceita `datetime`/`date`, serial Excel ou `dd/mm/yyyy`."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        if not MIN_DATE_SERIAL <= value <= MAX_DATE_SERIAL:
            return None
        return _excel_serial_to_date(float(value))
    if isinstance(value, str):
        return _ddmmyyyy_to_date(value)
    return None


def find_header_row(rows: Iterable[Row], anchor: str, max_rows: int = 10) -> int | None:
    """Localiza a linha de cabeçalhos pela coluna-âncora, nas primeiras linhas."""
    target = anchor.lower()
    for index, row in enumerate(rows):
        if index >= max_rows:
            return None
        if any(cell_text(cell).lower().startswith(target) for cell in row):
            return index
    return None


def validate_headers(header_row: Row, expected: Sequence[str]) -> list[str]:
    """Devolve os cabeçalhos esperados que faltam na linha (comparação por prefixo)."""
    present = [cell_text(cell).lower() for cell in header_row]
    return [
        header
        for header in expected
        if not any(cell.startswith(header.lower()) for cell in present)
    ]
