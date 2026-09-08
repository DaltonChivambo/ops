"""Quem está autenticado, do ponto de vista da aplicação.

O token do GEEA traz muito mais do que isto — `session_state`, `at_hash`,
`allowed-origins` e o resto do que um Keycloak põe lá dentro. O que atravessa
a fronteira para dentro do MozaOps é só o que a aplicação usa, e nada mais:
assim o dia em que a forma do token mudar mexe num sítio, não em todos.

As **áreas não vêm do token**: são decididas por `areas.py`. O GEEA diz a que
unidade orgânica a pessoa pertence; o MozaOps decide o que essa unidade abre.

Não há papéis. Dentro de uma área, quem opera, quem supervisiona e quem chefia
fazem hoje exactamente o mesmo trabalho no sistema — inventar três níveis para
os distinguir era escrever uma regra que ninguém pediu.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Principal:
    """O sujeito de um pedido autenticado."""

    subject: str
    username: str
    name: str
    email: str
    #: As áreas do MozaOps que esta pessoa pode abrir. Vazio = entra e não vê nada.
    areas: frozenset[str]
    #: `department_code` e `department` são os nomes das claims do GEEA. O que
    #: lá está é a unidade orgânica — que tanto pode ser um departamento como
    #: uma área, um serviço ou um gabinete. Guardam-se com o nome do contrato
    #: de quem os emite, para o mapeamento ser o único sítio a interpretá-los.
    department_code: str
    department: str
    function: str
    employee_id: str

    def has_area(self, area: str) -> bool:
        return area in self.areas
