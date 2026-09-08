"""Identidade do GEEA → papéis do MozaOps. Puro: sem I/O, sem HTTP.

O GEEA autentica, mas não sabe o que é um «supervisor» aqui dentro: os papéis
que traz no token (`work_queue`, `manage_employee`, `manage_organicUnit`) são
do sistema dele. Alguém tem de decidir, e essa decisão é nossa — por isso vive
em código nosso, testável sem rede.

**Ordem de precedência**, do mais forte para o mais fraco:

1. Papéis do GEEA com o prefixo acordado (`mozaops_supervisor`). Hoje não
   existem; no dia em que a equipa de IAM os criar, passam a mandar e as
   regras abaixo deixam de se aplicar a quem os tiver — é assim que esta
   tabela desaparece sem ninguém ter de a apagar de uma vez.
2. Lista explícita por utilizador. É o que desbloqueia o primeiro dia.
3. Departamento e função, para não obrigar a listar pessoa a pessoa.
4. Nada. **Não há papel por omissão**: um `operator` de recurso daria escrita
   sobre casos do departamento a qualquer pessoa do banco que consiga
   autenticar-se. Quem não corresponder entra e cai em «sem permissão».

`supervisor` traz sempre `operator` atrás — é como o papel composto do
Keycloak se comportava, e é o que o `roles.ts` do frontend documenta.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from mozaops_libs.auth.principal import ROLES, Role


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


@dataclass(frozen=True, slots=True)
class RoleMapping:
    """As regras, já normalizadas. Construída uma vez, a partir da configuração."""

    supervisor_users: frozenset[str] = field(default_factory=frozenset)
    auditor_users: frozenset[str] = field(default_factory=frozenset)
    operator_users: frozenset[str] = field(default_factory=frozenset)
    operator_departments: frozenset[str] = field(default_factory=frozenset)
    supervisor_functions: frozenset[str] = field(default_factory=frozenset)
    role_claim_prefix: str = "mozaops_"


def _with_implied(roles: set[Role]) -> frozenset[Role]:
    if "supervisor" in roles:
        roles.add("operator")
    return frozenset(roles)


def _from_claim_roles(claims: dict[str, Any], prefix: str) -> frozenset[Role]:
    if not prefix:
        return frozenset()

    realm_access = claims.get("realm_access") or {}
    claimed = realm_access.get("roles") or []

    found: set[Role] = set()
    for entry in claimed:
        if not isinstance(entry, str) or not entry.startswith(prefix):
            continue
        candidate = entry.removeprefix(prefix)
        # O `in ROLES` estreita para `Role`: o mypy segue o `Literal`.
        if candidate in ROLES:
            found.add(candidate)
    return _with_implied(found)


def _from_user_lists(username: str, mapping: RoleMapping) -> frozenset[Role]:
    found: set[Role] = set()
    if username in mapping.supervisor_users:
        found.add("supervisor")
    if username in mapping.auditor_users:
        found.add("auditor")
    if username in mapping.operator_users:
        found.add("operator")
    return _with_implied(found)


def _from_department(claims: dict[str, Any], mapping: RoleMapping) -> frozenset[Role]:
    department_code = str(claims.get("departmentCode") or "").strip()
    if not department_code or department_code not in mapping.operator_departments:
        return frozenset()

    function = str(claims.get("function") or "").strip()
    if function and function in mapping.supervisor_functions:
        return _with_implied({"supervisor"})
    return frozenset({"operator"})


def map_roles(claims: dict[str, Any], mapping: RoleMapping) -> frozenset[Role]:
    """Aplica as regras por ordem e devolve na primeira que der resultado."""
    username = str(claims.get("preferred_username") or "").strip()

    for candidate in (
        _from_claim_roles(claims, mapping.role_claim_prefix),
        _from_user_lists(username, mapping),
        _from_department(claims, mapping),
    ):
        if candidate:
            return candidate

    return frozenset()
