"""A ponte para o FastAPI: dependências de rota e tradução de erros.

É o único ficheiro da lib que sabe o que é HTTP. As camadas de baixo
(`verifier`, `areas`, `access`, `principal`) não importam nada daqui, e por isso
testam-se sem cliente nem aplicação.

**O envelope é contrato.** O `HTTPException` do FastAPI responde
`{"detail": ...}`, e o `error.interceptor.ts` do SPA não sabe ler essa forma —
cai na mensagem genérica de «erro inesperado». Daí registarem-se handlers em vez
de se levantar `HTTPException`.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from mozaops_libs.auth.access import AccessLevel, client_roles, parse_service_access
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


def display_name(claims: dict[str, Any]) -> str:
    """O nome como se mostra a alguém, a partir do que o GEEA registou.

    O directório repete o apelido no `name` de quem tem mais do que um nome
    próprio — «Dalton Chivambo Chivambo», quando o apelido é «Chivambo» — e é
    essa repetição que se corta, e só ela. Ficar pelo `given_name` cortava
    também o apelido de quem não tem a repetição, e mostrava «John» a John Doe.
    """
    name = " ".join(str(claims.get("name") or "").split())
    if name:
        parts = name.split(" ")
        return " ".join(parts[:-1]) if len(parts) > 2 and parts[-1] == parts[-2] else name
    return str(claims.get("given_name") or claims.get("preferred_username") or "")


def principal_from_claims(claims: dict[str, Any], mapping: AreaMapping, client: str) -> Principal:
    roles = client_roles(claims, client)
    return Principal(
        subject=str(claims.get("sub") or ""),
        username=str(claims.get("preferred_username") or ""),
        name=display_name(claims),
        email=str(claims.get("email") or ""),
        areas=map_areas(claims, mapping, roles),
        service_access=parse_service_access(roles),
        department_code=str(claims.get("departmentCode") or ""),
        department=str(claims.get("department") or ""),
        function=str(claims.get("function") or ""),
        # O GEEA usa mesmo uma chave com espaço e maiúsculas; é o contrato dele.
        employee_id=str(claims.get("Employee ID") or ""),
    )


class Auth:
    """Construída uma vez, no arranque do serviço, a partir da configuração."""

    def __init__(self, verifier: TokenVerifier, mapping: AreaMapping, client: str):
        self._verifier = verifier
        self._mapping = mapping
        self._client = client

    async def principal(
        self,
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    ) -> Principal:
        if credentials is None or not credentials.credentials:
            raise UnauthenticatedError

        claims = await self._verifier.verify(credentials.credentials)
        principal = principal_from_claims(claims, self._mapping, self._client)
        # O middleware de auditoria corre fora da rota e não tem como pedir
        # dependências; é por aqui que lhe chega quem está do outro lado.
        request.state.principal = principal
        return principal

    def require_access(self, service: str, area: str) -> Callable[..., Awaitable[Principal]]:
        """Dependência que exige acesso a um microserviço.

        Quem é da área passa como sempre passou. Quem não é passa se lhe tiverem
        concedido este serviço com nível suficiente — e o nível sai do método,
        não de uma lista de rotas que alguém teria de manter.

        Devolver o `Principal` em vez de `None` deixa a mesma dependência servir
        de guarda e de fonte de quem está a pedir.
        """

        async def guard(
            request: Request, principal: Principal = Depends(self.principal)
        ) -> Principal:
            required = AccessLevel.required_for(request.method)
            if not principal.is_allowed(service, area, required):
                raise ForbiddenError
            return principal

        return guard


def register_error_handlers(app: FastAPI) -> None:
    """Liga os erros de autenticação ao envelope da aplicação."""

    @app.exception_handler(AuthError)
    async def handle_auth_error(_request: Request, error: Exception) -> JSONResponse:
        for error_type, status, code in _STATUS_BY_ERROR:
            if isinstance(error, error_type):
                # O `WWW-Authenticate` no 401 é o que a norma manda, e o que diz
                # a um cliente que o caminho é renovar a sessão.
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
