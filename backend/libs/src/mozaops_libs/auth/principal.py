"""Quem está autenticado, do ponto de vista da aplicação.

O token do GEEA traz muito mais do que isto — `session_state`, `at_hash`,
`allowed-origins` e o resto do que um Keycloak põe lá dentro. O que atravessa a
fronteira para dentro do MozaOps é só o que a aplicação usa, e nada mais.

**Nada aqui distingue pessoa de programa.** Os dois autenticam-se da mesma
maneira e recebem os acessos da mesma maneira; o que varia é o que lhes foi
concedido. Uma distinção que o código nunca testa seria peso morto — e amarrava
a autorização à forma como o token foi obtido, que é justamente o que há de
mudar quando os programas passarem a autenticar-se por segredo de cliente.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from mozaops_libs.auth.access import AccessLevel
from mozaops_libs.auth.areas import ALL_AREAS


@dataclass(frozen=True, slots=True)
class Principal:
    """O sujeito de um pedido autenticado."""

    subject: str
    username: str
    name: str
    email: str
    #: As áreas do MozaOps que abre. `ALL_AREAS` vale por todas, incluindo as
    #: que ainda não existem.
    areas: frozenset[str]
    #: id do microserviço → o que lá pode fazer. A concessão fina, para quem não
    #: é da área.
    service_access: Mapping[str, AccessLevel]
    #: `department_code` e `department` são os nomes das claims do GEEA. O que
    #: lá está é a unidade orgânica — que tanto pode ser um departamento como
    #: uma área, um serviço ou um gabinete.
    department_code: str
    department: str
    function: str
    employee_id: str

    def has_area(self, area: str) -> bool:
        return ALL_AREAS in self.areas or area in self.areas

    def access_to(self, service: str) -> AccessLevel | None:
        return self.service_access.get(service)

    def is_allowed(self, service: str, area: str, required: AccessLevel) -> bool:
        """Quem é da área faz tudo; os outros, o que lhes foi concedido."""
        if self.has_area(area):
            return True
        granted = self.access_to(service)
        return granted is not None and granted >= required
