"""Acesso a um microserviço, concedido papel a papel pelo realm.

A área diz de que departamento se é e abre as automações todas dele. Isto é a
concessão fina, para quem precisa de uma automação só — uma pessoa que consulta
sem mexer, ou um programa que integra connosco. Vale para os dois da mesma
maneira, e é por isso que nada aqui distingue pessoa de programa.
"""

from collections.abc import Iterable, Mapping
from enum import IntEnum
from types import MappingProxyType
from typing import Any

SERVICE_ROLE_PREFIX = "service:"

#: Métodos que não mudam estado. A guarda usa-os para saber o nível exigido, em
#: vez de uma lista de rotas que alguém teria de manter sincronizada.
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


class AccessLevel(IntEnum):
    """`IntEnum` para que `WRITE >= READ` seja a própria ordem."""

    READ = 1
    WRITE = 2

    @classmethod
    def parse(cls, value: str) -> "AccessLevel | None":
        try:
            return cls[value.strip().upper()]
        except KeyError:
            return None

    @classmethod
    def required_for(cls, method: str) -> "AccessLevel":
        return cls.READ if method.upper() in SAFE_METHODS else cls.WRITE


def client_roles(claims: dict[str, Any], client: str) -> frozenset[str]:
    """Os papéis que o realm atribui ao **nosso** cliente.

    O cliente vem da configuração e não do `azp` do token: quem pede o token
    deixa de ser quem nos diz o que pode fazer, e admitir mais um cliente passa
    a ser admitir um cliente, e não delegar-lhe a atribuição dos nossos acessos.
    """
    if not client:
        return frozenset()

    resource_access = claims.get("resource_access")
    if not isinstance(resource_access, dict):
        return frozenset()

    entry = resource_access.get(client)
    if not isinstance(entry, dict):
        return frozenset()

    roles = entry.get("roles")
    if not isinstance(roles, list):
        return frozenset()

    return frozenset(role.strip() for role in roles if isinstance(role, str) and role.strip())


def parse_service_access(roles: Iterable[str]) -> Mapping[str, AccessLevel]:
    """`service:<serviço>:<read|write>` → `{serviço: nível}`, o mais alto vence.

    Um papel sem sufixo, ou com um sufixo desconhecido, não abre nada: quem
    atribui papéis no realm não conhece as nossas convenções, e um engano de
    escrita tem de falhar fechado.
    """
    access: dict[str, AccessLevel] = {}

    for role in roles:
        if not role.startswith(SERVICE_ROLE_PREFIX):
            continue

        service, separator, suffix = role[len(SERVICE_ROLE_PREFIX) :].rpartition(":")
        level = AccessLevel.parse(suffix) if separator else None
        if not service or level is None:
            continue

        granted = access.get(service)
        if granted is None or level > granted:
            access[service] = level

    return MappingProxyType(access)
