"""Dependências FastAPI de autenticação e autorização.

Usadas pela camada `api/` dos serviços. Nada abaixo de `api/` importa isto.

`build_auth_dependencies` devolve o trio já ligado entre si — é preciso porque os guards de
papel têm de saber como resolver o utilizador, e esse `Depends` é construído em runtime com o
`JwksClient` que o serviço criou no lifespan.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ops_common.auth.jwks import JwksClient, TokenInvalido, decode_token
from ops_common.auth.models import CurrentUser

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthDependencies:
    """O que o `api/v1/dependencies.py` de cada serviço reexporta."""

    get_current_user: Callable[..., CurrentUser]
    require_roles: Callable[..., Callable[..., CurrentUser]]
    require_permissions: Callable[..., Callable[..., CurrentUser]]


def build_auth_dependencies(
    jwks_client: JwksClient,
    issuer: str,
    audience: str,
    algorithms: list[str] | None = None,
) -> AuthDependencies:
    def get_current_user(
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    ) -> CurrentUser:
        if credentials is None or not credentials.credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais em falta",
                headers={"WWW-Authenticate": "Bearer"},
            )
        try:
            claims = decode_token(
                credentials.credentials,
                jwks_client=jwks_client,
                issuer=issuer,
                audience=audience,
                algorithms=algorithms,
            )
        except TokenInvalido as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

        user = CurrentUser.model_validate(claims)
        request.state.user = user
        return user

    def require_roles(*roles: str) -> Callable[..., CurrentUser]:
        def _guard(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
            if not user.has_role(*roles):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Requer um dos papéis: {', '.join(roles)}",
                )
            return user

        return _guard

    def require_permissions(*permissions: str) -> Callable[..., CurrentUser]:
        def _guard(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
            if not user.has_permission(*permissions):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Requer uma das permissões: {', '.join(permissions)}",
                )
            return user

        return _guard

    return AuthDependencies(
        get_current_user=get_current_user,
        require_roles=require_roles,
        require_permissions=require_permissions,
    )
