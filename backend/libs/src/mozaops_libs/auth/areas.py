"""Quem entra em que área do MozaOps. Puro: sem I/O, sem HTTP.

**Área** é a unidade de acesso do MozaOps, e é a mesma coisa que o catálogo do
frontend mostra na barra lateral (`channels` = «Canais»). Quem é da área faz
tudo o que as automações dela fazem — não há papéis lá dentro, porque operador,
supervisor e chefe fazem hoje o mesmo trabalho no sistema.

Para dar acesso a uma automação só, ou sem escrita, existe a concessão por
microserviço em `access.py`. As duas somam-se.

**De onde vêm as áreas**, por ordem de importância:

1. Os papéis do nosso cliente no token, onde o nome do papel **é** o id da área.
   É o realm a provisionar, no sítio onde a equipa de IAM já provisiona tudo o
   resto. A excepção é o `ALL_AREAS`, que vale por todas.
2. Unidade orgânica (`AUTH_AREAS`), a partir da claim `departmentCode` — rede
   para as unidades que o realm ainda não provisionou.
3. Lista explícita por utilizador (`AUTH_AREA_USERS`), para quem está registado
   noutra unidade mas trabalha nesta.
4. Nada. **Não há área por omissão**: uma de recurso daria a plataforma a
   qualquer pessoa do banco que consiga autenticar-se.

As três primeiras somam-se, e tirar acesso faz-se tirando-o em todas.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from mozaops_libs.auth.access import SERVICE_ROLE_PREFIX

#: O papel que abre o MozaOps inteiro, incluindo as áreas que ainda não existem.
#: Quem o tem entra em qualquer sítio, logo dá-se a quem se daria a chave toda.
ALL_AREAS = "all-areas"


def parse_set(raw: str | Iterable[str] | None) -> frozenset[str]:
    """`"a, b ,,c"` → `{"a", "b", "c"}`.

    As listas chegam de variáveis de ambiente, onde uma vírgula a mais não deve
    criar uma entrada vazia que depois corresponde a um `username` vazio.
    """
    if raw is None:
        return frozenset()
    values = raw.split(",") if isinstance(raw, str) else raw
    return frozenset(item.strip() for item in values if item and item.strip())


def parse_area_map(raw: str | None) -> dict[str, frozenset[str]]:
    """`"pos:2350,2442; cartoes:2360"` → `{"pos": {...}, "cartoes": {...}}`.

    Entradas sem `:`, ou com a área vazia, são ignoradas em silêncio: o que aqui
    rebentasse deixava o serviço sem arrancar por causa de uma vírgula.
    """
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
    """As áreas que estas claims abrem. Vazio quando nenhuma abre."""
    unit = str(claims.get("departmentCode") or "").strip()
    username = str(claims.get("preferred_username") or "").strip()

    found = {role for role in roles if not role.startswith(SERVICE_ROLE_PREFIX)}
    found |= {area for area, users in mapping.by_user.items() if username and username in users}
    if unit:
        found |= {area for area, units in mapping.by_unit.items() if unit in units}
    return frozenset(found)
