"""Quem está autenticado, do ponto de vista da aplicação."""

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
    #: Áreas que abre; `ALL_AREAS` vale por todas.
    areas: frozenset[str]
    #: id do microserviço → o que lá pode fazer.
    service_access: Mapping[str, AccessLevel]
    #: Nomes das claims do GEEA; o valor é a unidade orgânica.
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
