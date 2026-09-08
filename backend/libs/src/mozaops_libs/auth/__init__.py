"""Autenticação partilhada: validar tokens do GEEA e decidir papéis.

Está em `libs/` e não dentro de um serviço porque tem dois consumidores desde
o primeiro dia — o `platform/identity` e o `closing-credit-validation`. E
porque autenticação diferente entre dois serviços da mesma aplicação não é
diferença de estilo: é a porta que fica aberta no serviço que ficou para trás.
"""

from mozaops_libs.auth.errors import (
    AuthError,
    ForbiddenError,
    IdentityUnavailableError,
    UnauthenticatedError,
)
from mozaops_libs.auth.fastapi import Auth, principal_from_claims, register_error_handlers
from mozaops_libs.auth.mapping import RoleMapping, map_roles, parse_set
from mozaops_libs.auth.principal import (
    READERS,
    RESOLVERS,
    ROLES,
    WRITERS,
    Principal,
    Role,
)
from mozaops_libs.auth.verifier import TokenVerifier

__all__ = [
    "READERS",
    "RESOLVERS",
    "ROLES",
    "WRITERS",
    "Auth",
    "AuthError",
    "ForbiddenError",
    "IdentityUnavailableError",
    "Principal",
    "Role",
    "RoleMapping",
    "TokenVerifier",
    "UnauthenticatedError",
    "map_roles",
    "parse_set",
    "principal_from_claims",
    "register_error_handlers",
]
