"""Quem entra em que área do MozaOps. Puro: sem I/O, sem HTTP."""

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from mozaops_libs.auth.access import SERVICE_ROLE_PREFIX

#: O papel que abre o MozaOps inteiro, áreas futuras incluídas.
ALL_AREAS = "all-areas"


def parse_set(raw: str | Iterable[str] | None) -> frozenset[str]:
    """`"a, b ,,c"` → `{"a", "b", "c"}`."""
    if raw is None:
        return frozenset()
    values = raw.split(",") if isinstance(raw, str) else raw
    return frozenset(item.strip() for item in values if item and item.strip())


def parse_area_map(raw: str | None) -> dict[str, frozenset[str]]:
    """`"pos:2350,2442; cartoes:2360"` → `{"pos": {...}, "cartoes": {...}}`."""
    mapping: dict[str, frozenset[str]] = {}
    if not raw:
        return mapping

    for entry in raw.split(";"):
        area, _, values = entry.partition(":")
        area = area.strip()
        members = parse_set(values)
        if not area or not members:
            continue
        mapping[area] = mapping.get(area, frozenset()) | members
    return mapping


@dataclass(frozen=True, slots=True)
class AreaMapping:
    """As regras, já normalizadas. Construída uma vez, a partir da configuração."""

    #: área do MozaOps → códigos de unidade orgânica do GEEA.
    by_unit: dict[str, frozenset[str]] = field(default_factory=dict)
    #: área do MozaOps → `username`, para os casos que a unidade não cobre.
    by_user: dict[str, frozenset[str]] = field(default_factory=dict)

    @property
    def areas(self) -> frozenset[str]:
        """Todas as áreas que a configuração conhece. Serve os diagnósticos."""
        return frozenset(self.by_unit) | frozenset(self.by_user)


def map_areas(claims: dict[str, Any], mapping: AreaMapping, roles: Iterable[str]) -> frozenset[str]:
    """As áreas que estas claims abrem. Vazio quando nenhuma abre.

    Não há área por omissão: uma de recurso daria a plataforma a quem não a tem.
    """
    unit = str(claims.get("departmentCode") or "").strip()
    username = str(claims.get("preferred_username") or "").strip()

    found = {role for role in roles if not role.startswith(SERVICE_ROLE_PREFIX)}
    found |= {area for area, users in mapping.by_user.items() if username and username in users}
    if unit:
        found |= {area for area, units in mapping.by_unit.items() if unit in units}
    return frozenset(found)
