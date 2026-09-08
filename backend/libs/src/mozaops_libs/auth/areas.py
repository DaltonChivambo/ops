"""Unidade orgânica do GEEA → áreas do MozaOps. Puro: sem I/O, sem HTTP.

O GEEA autentica e diz a que unidade a pessoa pertence — a claim chama-se
`departmentCode`, mas o que lá vem tanto é um departamento (`2350`,
Departamento de Apoio Operacional) como uma área, um serviço ou um gabinete.
Quem decide o que cada uma dessas unidades abre no MozaOps somos nós, e por
isso a decisão vive em código nosso, testável sem rede.

**Área** é a unidade de acesso do MozaOps, e é a mesma coisa que o catálogo do
frontend mostra na barra lateral (`payments-and-channels` = «Meios de
Pagamentos e Canais»). Cada automação pertence a uma; quem não for da área não
a vê nem lhe chega pela API.

**Não há papéis dentro da área.** Operador, supervisor e chefe de departamento
fazem hoje o mesmo trabalho no sistema.

**Ordem de precedência**, do mais forte para o mais fraco:

1. Lista explícita por utilizador (`AUTH_AREA_USERS`). É o que dá acesso a
   quem está registado noutra unidade — o gestor do projecto, quem vem de
   fora ajudar num fecho — sem ter de abrir a unidade inteira.
2. Unidade orgânica (`AUTH_AREAS`), para não obrigar a listar pessoa a pessoa.
3. Nada. **Não há área por omissão**: uma de recurso daria a plataforma a
   qualquer pessoa do banco que consiga autenticar-se. Quem não corresponder
   entra e cai em «sem acesso».

As duas primeiras somam-se, ao contrário do que a palavra «precedência» faria
esperar: o acréscimo por utilizador é um acréscimo, e não uma substituição —
tirar a uma pessoa o que a unidade dela já lhe dá faz-se tirando-a da unidade.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any


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


def map_areas(claims: dict[str, Any], mapping: AreaMapping) -> frozenset[str]:
    """As áreas que estas claims abrem. Vazio quando nenhuma abre."""
    unit = str(claims.get("departmentCode") or "").strip()
    username = str(claims.get("preferred_username") or "").strip()

    found = {area for area, users in mapping.by_user.items() if username and username in users}
    if unit:
        found |= {area for area, units in mapping.by_unit.items() if unit in units}
    return frozenset(found)
