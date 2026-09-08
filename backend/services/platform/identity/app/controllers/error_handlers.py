"""Erro de domínio → resposta HTTP, no envelope que o SPA sabe ler.

O `{"error": {"code", "message"}}` é contrato: o `error.interceptor.ts` do SPA
depende desta forma exacta. Os erros de autenticação da lib partilhada trazem
os seus próprios handlers — ver `register` no fim.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.domain.errors import (
    DomainError,
    GeeaUnavailableError,
    InvalidCredentialsError,
    NoSessionError,
    TooManyAttemptsError,
)
from mozaops_libs.auth import register_error_handlers

logger = logging.getLogger("identity")

# Percorrido pela MRO da excepção, do mais específico para o mais geral.
STATUS_BY_ERROR: tuple[tuple[type[DomainError], int, str], ...] = (
    (InvalidCredentialsError, 401, "invalid_credentials"),
    (NoSessionError, 401, "unauthenticated"),
    (TooManyAttemptsError, 429, "too_many_attempts"),
    (GeeaUnavailableError, 503, "identity_unavailable"),
    (DomainError, 400, "bad_request"),
)


def _envelope(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def register(app: FastAPI) -> None:
    register_error_handlers(app)

    @app.exception_handler(DomainError)
    async def handle_domain_error(_request: Request, error: Exception) -> JSONResponse:
        for tipo, status, code in STATUS_BY_ERROR:
            if isinstance(error, tipo):
                return _envelope(status, code, str(error))
        return _envelope(400, "bad_request", str(error))

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation(_request: Request, _error: Exception) -> JSONResponse:
        """O 422 do FastAPI, vestido com o nosso envelope.

        **Sem detalhe do que falhou.** Num pedido de login, o corpo que falhou
        a validação leva a password lá dentro, e a resposta padrão do FastAPI
        devolve-a ao cliente dentro do `{"detail": [...]}`.
        """
        return _envelope(
            422,
            "bad_request",
            "O pedido tem parâmetros inválidos. Verifique os valores e tente de novo.",
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(_request: Request, error: Exception) -> JSONResponse:
        logger.exception("Erro inesperado", exc_info=error)
        return _envelope(
            500,
            "internal_error",
            "Ocorreu um erro inesperado no servidor. Tente novamente.",
        )
