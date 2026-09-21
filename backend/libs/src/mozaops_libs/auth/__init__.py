"""Autenticação partilhada: validar tokens do GEEA e decidir áreas.

Está em `libs/` porque tem dois consumidores — o `platform/auth-service` e o
`pos-closing-credit-validation` — e autenticação diferente entre dois serviços
da mesma aplicação é a porta que fica aberta no que ficou para trás.
"""

from mozaops_libs.auth.areas import (
    ALL_AREAS,
    AreaMapping,
    map_areas,
    parse_area_map,
    parse_set,
)
from mozaops_libs.auth.errors import (
    AuthError,
    ForbiddenError,
    IdentityUnavailableError,
    UnauthenticatedError,
)
from mozaops_libs.auth.fastapi import Auth, principal_from_claims, register_error_handlers
from mozaops_libs.auth.principal import Principal
from mozaops_libs.auth.verifier import TokenVerifier

__all__ = [
    "ALL_AREAS",
    "AreaMapping",
    "Auth",
    "AuthError",
    "ForbiddenError",
    "IdentityUnavailableError",
    "Principal",
    "TokenVerifier",
    "UnauthenticatedError",
    "map_areas",
    "parse_area_map",
    "parse_set",
    "principal_from_claims",
    "register_error_handlers",
]
