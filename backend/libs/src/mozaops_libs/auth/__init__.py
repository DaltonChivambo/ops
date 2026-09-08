"""Autenticação partilhada: validar tokens do GEEA e decidir áreas.

Está em `libs/` e não dentro de um serviço porque tem dois consumidores desde
o primeiro dia — o `platform/identity` e o `closing-credit-validation`. E
porque autenticação diferente entre dois serviços da mesma aplicação não é
diferença de estilo: é a porta que fica aberta no serviço que ficou para trás.
"""

from mozaops_libs.auth.areas import AreaMapping, map_areas, parse_area_map, parse_set
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
