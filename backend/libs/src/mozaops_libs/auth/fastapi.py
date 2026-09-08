"""A ponte para o FastAPI: dependências de rota e tradução de erros.

É o único ficheiro da lib que sabe o que é HTTP. As camadas de baixo
(`verifier`, `areas`, `principal`) não importam nada daqui, e por isso
testam-se sem cliente nem aplicação.

**O envelope é contrato.** O `HTTPException` do FastAPI responde
`{"detail": ...}`, e o `error.interceptor.ts` do SPA não sabe ler essa forma —
cai na mensagem genérica de «erro inesperado». As respostas de autenticação
saem no mesmo `{"error": {"code", "message"}}` que os erros de domínio de cada
serviço, por isso é que aqui se registam handlers em vez de se levantar
`HTTPException`.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from mozaops_libs.auth.areas import AreaMapping, map_areas
from mozaops_libs.auth.errors import (
    AuthError,
    ForbiddenError,
    IdentityUnavailableError,
    UnauthenticatedError,
)
from mozaops_libs.auth.principal import Principal
from mozaops_libs.auth.verifier import TokenVerifier

# `auto_error=False`: com o erro automático, o FastAPI responderia o seu
# `{"detail": "Not authenticated"}` antes de nós vermos o pedido — fora do
# envelope, e em inglês.
_bearer = HTTPBearer(auto_error=False)

_STATUS_BY_ERROR: tuple[tuple[type[AuthError], int, str], ...] = (
    (UnauthenticatedError, 401, "unauthenticated"),
    (ForbiddenError, 403, "forbidden"),
    (IdentityUnavailableError, 503, "identity_unavailable"),
)


def principal_from_claims(claims: dict[str, Any], mapping: AreaMapping) -> Principal:
    return Principal(
        subject=str(claims.get("sub") or ""),
        username=str(claims.get("preferred_username") or ""),
        name=str(claims.get("name") or claims.get("preferred_username") or ""),
        email=str(claims.get("email") or ""),
        areas=map_areas(claims, mapping),
        department_code=str(claims.get("departmentCode") or ""),
        department=str(claims.get("department") or ""),
        function=str(claims.get("function") or ""),
        # O GEEA usa mesmo uma chave com espaço e maiúsculas; é o contrato dele.
        employee_id=str(claims.get("Employee ID") or ""),
    )


class Auth:
    """Construída uma vez, no arranque do serviço, a partir da configuração.

    Expõe dependências já ligadas ao verificador e ao mapa de áreas — os
    controladores pedem `Depends(auth.principal)` e não conhecem nem um nem
    outro.
    """

    def __init__(self, verifier: TokenVerifier, mapping: AreaMapping):
        self._verifier = verifier
        self._mapping = mapping

    async def principal(
        self,
        credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    ) -> Principal:
        if credentials is None or not credentials.credentials:
            raise UnauthenticatedError

        claims = await self._verifier.verify(credentials.credentials)
        return principal_from_claims(claims, self._mapping)

    def require_area(self, area: str) -> Callable[..., Awaitable[Principal]]:
        """Dependência que exige acesso a uma área do MozaOps.

        Uma automação pertence a uma área e o serviço que a serve declara qual
        é — não há aqui uma lista de rotas por permissão, porque dentro da área
        toda a gente faz o mesmo.

        Devolver o `Principal` em vez de `None` deixa a mesma dependência
        servir de guarda e de fonte de quem está a pedir — a rota não precisa
        de o pedir duas vezes.
        """

        async def guard(principal: Principal = Depends(self.principal)) -> Principal:
            if not principal.has_area(area):
                raise ForbiddenError
            return principal

        return guard


def register_error_handlers(app: FastAPI) -> None:
    """Liga os erros de autenticação ao envelope da aplicação."""

    @app.exception_handler(AuthError)
    async def handle_auth_error(_request: Request, error: Exception) -> JSONResponse:
        for tipo, status, code in _STATUS_BY_ERROR:
            if isinstance(error, tipo):
                # O `WWW-Authenticate` no 401 é o que a norma manda, e o que
                # diz a um cliente que o caminho é renovar a sessão.
                headers = {"WWW-Authenticate": "Bearer"} if status == 401 else None
                return JSONResponse(
                    status_code=status,
                    content={"error": {"code": code, "message": str(error)}},
                    headers=headers,
                )
        return JSONResponse(
            status_code=401,
            content={"error": {"code": "unauthenticated", "message": str(error)}},
            headers={"WWW-Authenticate": "Bearer"},
        )
