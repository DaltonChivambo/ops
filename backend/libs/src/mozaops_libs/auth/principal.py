"""Quem está autenticado, do ponto de vista da aplicação.

O token do GEEA traz muito mais do que isto — `session_state`, `at_hash`,
`allowed-origins` e o resto do que um Keycloak põe lá dentro. O que atravessa
a fronteira para dentro do MozaOps é só o que a aplicação usa, e nada mais:
assim o dia em que a forma do token mudar mexe num sítio, não em todos.

Os papéis **não vêm do token**: são decididos por `mapping.py`. O GEEA diz
quem a pessoa é; o MozaOps decide o que ela pode fazer.
"""

from dataclasses import dataclass
from typing import Literal

Role = Literal["operator", "supervisor", "auditor"]

ROLES: tuple[Role, ...] = ("operator", "supervisor", "auditor")

#: Quem pode correr automações e editar casos.
WRITERS: frozenset[Role] = frozenset({"operator", "supervisor"})

#: Quem pode ver — toda a gente com acesso à plataforma.
READERS: frozenset[Role] = frozenset({"operator", "supervisor", "auditor"})

#: Marcar um caso como regularizado tem significado financeiro; não é do operador.
RESOLVERS: frozenset[Role] = frozenset({"supervisor"})


@dataclass(frozen=True, slots=True)
class Principal:
    """O sujeito de um pedido autenticado."""

    subject: str
    username: str
    name: str
    email: str
    roles: frozenset[Role]
    department_code: str
    department: str
    function: str
    employee_id: str

    def has_any(self, allowed: frozenset[Role]) -> bool:
        return bool(self.roles & allowed)
