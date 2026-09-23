"""Autenticação partilhada: validar tokens do GEEA e decidir acessos."""

from mozaops_libs.auth.access import (
    SERVICE_ROLE_PREFIX,
    AccessLevel,
    client_roles,
    parse_service_access,
)
from mozaops_libs.auth.areas import (
    ALL_AREAS,
    AreaMapping,
    map_areas,
    parse_area_map,
    parse_set,
)
from mozaops_libs.auth.audit import register_audit
from mozaops_libs.auth.error_handlers import register_error_handlers
from mozaops_libs.auth.errors import (
    AuthError,
    ForbiddenError,
    IdentityUnavailableError,
    UnauthenticatedError,
)
from mozaops_libs.auth.guard import Auth
from mozaops_libs.auth.principal import Principal, principal_from_claims
from mozaops_libs.auth.verifier import TokenVerifier

__all__ = [
    "ALL_AREAS",
    "SERVICE_ROLE_PREFIX",
    "AccessLevel",
    "AreaMapping",
    "Auth",
    "AuthError",
    "ForbiddenError",
    "IdentityUnavailableError",
    "Principal",
    "TokenVerifier",
    "UnauthenticatedError",
    "client_roles",
    "map_areas",
    "parse_area_map",
    "parse_service_access",
    "parse_set",
    "principal_from_claims",
    "register_audit",
    "register_error_handlers",
]
