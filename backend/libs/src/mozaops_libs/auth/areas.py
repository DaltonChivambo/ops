"""Quem entra em que área do MozaOps. Puro: sem I/O, sem HTTP.

**Área** é a unidade de acesso do MozaOps, e é a mesma coisa que o catálogo do
frontend mostra na barra lateral (`channels` = «Canais»). Cada automação
pertence a uma; quem não for da área não a vê nem lhe chega pela API.

**Não há papéis dentro da área.** Operador, supervisor e chefe de departamento
fazem hoje o mesmo trabalho no sistema. Os «papéis» de que esta camada fala são
outra coisa: são os papéis que o realm atribui ao **nosso cliente**, e que têm o
nome da área que abrem.

**De onde vêm as áreas**, por ordem de importância:

1. Os papéis do cliente no token — `resource_access[azp].roles`, hoje
   `qa-mozaops`. É o realm QAS a dizer o que esta pessoa abre no MozaOps, e é a
   fonte principal: quem provisiona acessos é a equipa de IAM, no sítio onde já
   provisiona tudo o resto. O nome do papel **é** o id da área, por isso mudar
   um sem o outro tira o acesso. A excepção é o `ALL_AREAS`, que vale por
   todas.
2. Unidade orgânica (`AUTH_AREAS`), a partir da claim `departmentCode` — o que
   lá vem tanto é um departamento (`2350`, Departamento de Apoio Operacional)
   como uma área, um serviço ou um gabinete. Fica como rede para as unidades
   que o realm ainda não provisionou.
3. Lista explícita por utilizador (`AUTH_AREA_USERS`), para quem está registado
   noutra unidade mas trabalha nesta, sem ter de abrir a unidade inteira.
4. Nada. **Não há área por omissão**: uma de recurso daria a plataforma a
   qualquer pessoa do banco que consiga autenticar-se. Quem não corresponder
   entra e cai em «sem acesso».

As três primeiras **somam-se**: nenhuma substitui a outra, e tirar acesso a
alguém faz-se tirando-lho em todas — no realm e na configuração.

Só contam os papéis do cliente. Os de `realm_access` são do sistema de workflow
do banco (`manage_employee`, `work_queue`) e não dizem nada sobre o MozaOps,
mesmo quando por acaso têm um nome parecido.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

#: O papel que abre o MozaOps inteiro, incluindo as áreas que ainda não
#: existem. É para quem tem de ver tudo — a direcção, quem monta a plataforma —
#: e evita ter de voltar ao realm a cada automação nova.
#:
#: Não é um papel como os outros: os outros têm o nome da área que abrem, e
#: este não abre nenhuma em particular. Quem o tem entra em qualquer sítio,
#: logo dá-se a quem se daria a chave toda, e não por comodidade.
ALL_AREAS = "all-areas"


def parse_set(raw: str | Iterable[str] | None) -> frozenset[str]:
    """`"a, b ,,c"` → `{"a", "b", "c"}`.

    As listas chegam de variáveis de ambiente, onde uma vírgula a mais ou um
    espaço a sobrar não deve mudar o resultado — nem criar uma entrada vazia
    que depois corresponde a um `username` vazio.
    """
    if raw is None:
        return frozenset()
    values = raw.split(",") if isinstance(raw, str) else raw
    return frozenset(item.strip() for item in values if item and item.strip())


def parse_area_map(raw: str | None) -> dict[str, frozenset[str]]:
    """`"pos:2350,2442; cartoes:2360"` → `{"pos": {...}, "cartoes": {...}}`.

    Uma linha só, numa variável de ambiente, porque é assim que o compose e o
    `.env` a sabem passar. A área vem primeiro por ser o que se lê primeiro
    quando se procura «quem entra em X».

    Entradas sem `:`, ou com a área vazia, são ignoradas em silêncio: o que
    aqui rebentasse deixava o serviço sem arrancar por causa de uma vírgula.
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


def client_roles(claims: dict[str, Any]) -> frozenset[str]:
    """Os papéis que o realm atribui ao cliente que pediu este token.

    O cliente é o do `azp`, e não um nome escrito aqui: o verificador já só
    deixa passar tokens de um cliente nosso, e ir buscar os papéis a outro
    bloco de `resource_access` era ler os acessos que alguém tem noutra
    aplicação do banco.

    O que não tenha a forma esperada não abre nada — um `resource_access` sem o
    nosso cliente é o caso normal de quem o realm ainda não provisionou.
    """
    azp = str(claims.get("azp") or "").strip()
    if not azp:
        return frozenset()

    resource_access = claims.get("resource_access")
    if not isinstance(resource_access, dict):
        return frozenset()

    entry = resource_access.get(azp)
    if not isinstance(entry, dict):
        return frozenset()

    roles = entry.get("roles")
    if not isinstance(roles, list):
        return frozenset()

    return parse_set(role for role in roles if isinstance(role, str))


def map_areas(claims: dict[str, Any], mapping: AreaMapping) -> frozenset[str]:
    """As áreas que estas claims abrem. Vazio quando nenhuma abre."""
    unit = str(claims.get("departmentCode") or "").strip()
    username = str(claims.get("preferred_username") or "").strip()

    found = set(client_roles(claims))
    found |= {area for area, users in mapping.by_user.items() if username and username in users}
    if unit:
        found |= {area for area, units in mapping.by_unit.items() if unit in units}
    return frozenset(found)
