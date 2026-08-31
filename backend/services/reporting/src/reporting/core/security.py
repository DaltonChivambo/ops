"""Verificação do JWT emitido pelo Keycloak.

O OSB roteia e faz o corte grosso, mas não é o único ponto de verificação: cada serviço valida
o token localmente contra o JWKS do realm (`ops_common.auth`).
"""

from __future__ import annotations

from functools import lru_cache

from ops_common.auth import AuthDependencies, build_auth_dependencies

from reporting.core.config import get_settings


@lru_cache
def get_auth() -> AuthDependencies:
    settings = get_settings()
    return build_auth_dependencies(
        jwks_url=settings.jwks_endpoint,
        issuer=settings.issuer,
        audience=settings.keycloak_client_id,
        algorithms=[settings.jwt_algorithm],
    )
