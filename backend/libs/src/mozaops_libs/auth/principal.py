"""Quem está autenticado, do ponto de vista da aplicação."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from mozaops_libs.auth.access import AccessLevel, client_roles, parse_service_access
from mozaops_libs.auth.areas import ALL_AREAS, AreaMapping, map_areas


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


def display_name(claims: dict[str, Any]) -> str:
    """O nome como se mostra a alguém, a partir do que o GEEA registou."""
    name = " ".join(str(claims.get("name") or "").split())
    if name:
        parts = name.split(" ")
        return " ".join(parts[:-1]) if len(parts) > 2 and parts[-1] == parts[-2] else name
    return str(claims.get("given_name") or claims.get("preferred_username") or "")


def principal_from_claims(claims: dict[str, Any], mapping: AreaMapping, client: str) -> Principal:
    """O `Principal` que estas claims descrevem, com as áreas já resolvidas."""
    roles = client_roles(claims, client)
    return Principal(
        subject=str(claims.get("sub") or ""),
        username=str(claims.get("preferred_username") or ""),
        name=display_name(claims),
        email=str(claims.get("email") or ""),
        areas=map_areas(claims, mapping, roles),
        service_access=parse_service_access(roles),
        department_code=str(claims.get("departmentCode") or ""),
        department=str(claims.get("department") or ""),
        function=str(claims.get("function") or ""),
        # A claim do GEEA tem mesmo espaço e maiúsculas.
        employee_id=str(claims.get("Employee ID") or ""),
    )
