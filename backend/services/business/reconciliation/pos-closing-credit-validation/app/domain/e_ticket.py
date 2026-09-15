"""O e-Ticket de um caso — a referência do pedido aberto na SIMO.

É texto livre escrito à mão, que vai parar à base de dados, ao ecrã de outros
operadores e ao relatório Excel do departamento. Por isso não se guarda o que
vier: guarda-se uma referência, com forma de referência.

**A forma é deliberadamente estreita.** Letras, algarismos e os separadores que
as referências costumam ter (`-`, `_`, `/`, `.`), a começar por letra ou
algarismo. Começar assim fecha a porta à injecção de fórmulas no Excel (`=`,
`+`, `-`, `@` à cabeça), e sem espaços nem caracteres de controlo não há
referências que pareçam iguais e não sejam.

Validado aqui, e não num `Field(pattern=...)` do Pydantic, pela mesma razão do
`sla.py`: a mensagem que chega ao operador é em português e nasce no domínio.
"""

import re

from app.domain.errors import InvalidETicketError

MAX_E_TICKET_LENGTH = 40

_E_TICKET = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]*")


def normalize_e_ticket(raw: object) -> str | None:
    """O e-Ticket pronto a guardar, ou `None` para o apagar.

    Vazio (ou só espaços) apaga — é assim que o operador tira um e-Ticket
    posto por engano. Tudo o resto ou tem forma de referência, ou é recusado.
    """
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise InvalidETicketError("O e-Ticket tem de ser texto.")

    value = raw.strip()
    if not value:
        return None
    if len(value) > MAX_E_TICKET_LENGTH:
        raise InvalidETicketError(
            f"O e-Ticket tem no máximo {MAX_E_TICKET_LENGTH} caracteres."
        )
    if not _E_TICKET.fullmatch(value):
        raise InvalidETicketError(
            "O e-Ticket só pode ter letras, algarismos e os separadores - _ / . "
            "— e tem de começar por letra ou algarismo."
        )
    return value
