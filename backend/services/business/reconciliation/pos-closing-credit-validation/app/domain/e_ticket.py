"""O e-Ticket de um caso — a referência do pedido aberto na SIMO."""

import re

from app.domain.errors import InvalidETicketError

MAX_E_TICKET_LENGTH = 40

_E_TICKET = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]*")


def normalize_e_ticket(raw: object) -> str | None:
    """O e-Ticket pronto a guardar, ou `None` para o apagar."""
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise InvalidETicketError("O e-Ticket tem de ser texto.")

    value = raw.strip()
    if not value:
        return None
    if len(value) > MAX_E_TICKET_LENGTH:
        raise InvalidETicketError(f"O e-Ticket tem no máximo {MAX_E_TICKET_LENGTH} caracteres.")
    if not _E_TICKET.fullmatch(value):
        raise InvalidETicketError(
            "O e-Ticket só pode ter letras, algarismos e os separadores - _ / . "
            "— e tem de começar por letra ou algarismo."
        )
    return value
