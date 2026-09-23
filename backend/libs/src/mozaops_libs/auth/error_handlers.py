"""Erro de autenticação → resposta HTTP, no envelope que o SPA lê."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from mozaops_libs.auth.errors import (
    AuthError,
    ForbiddenError,
    IdentityUnavailableError,
    UnauthenticatedError,
)

_STATUS_BY_ERROR: tuple[tuple[type[AuthError], int, str], ...] = (
    (UnauthenticatedError, 401, "unauthenticated"),
    (ForbiddenError, 403, "forbidden"),
    (IdentityUnavailableError, 503, "identity_unavailable"),
)


def register_error_handlers(app: FastAPI) -> None:
    """Liga os erros de autenticação ao envelope da aplicação."""

    @app.exception_handler(AuthError)
    async def handle_auth_error(_request: Request, error: Exception) -> JSONResponse:
        for error_type, status, code in _STATUS_BY_ERROR:
            if isinstance(error, error_type):
                # `WWW-Authenticate`: diz ao cliente para renovar a sessão.
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
