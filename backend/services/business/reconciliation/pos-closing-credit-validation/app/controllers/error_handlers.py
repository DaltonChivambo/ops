"""Excepção de domínio → resposta HTTP. O único sítio que conhece os dois lados.

O envelope `{"error": {"code", "message"}}` é contrato com o `error.interceptor.ts`
do SPA, que não sabe ler o `{"detail": ...}` do FastAPI.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.domain.errors import (
    BusinessRuleError,
    DomainError,
    NotFoundError,
    NothingToUpdateError,
    UploadTooLargeError,
)
from mozaops_libs.auth import register_error_handlers

logger = logging.getLogger("pos_closing_credit_validation")

# Percorrido pela MRO da excepção, do mais específico para o mais geral.
STATUS_BY_ERROR: tuple[tuple[type[DomainError], int, str], ...] = (
    (NotFoundError, 404, "not_found"),
    # Antes do `BusinessRuleError`, de quem é subclasse.
    (UploadTooLargeError, 413, "payload_too_large"),
    (BusinessRuleError, 422, "business_rule"),
    (NothingToUpdateError, 400, "bad_request"),
    (DomainError, 400, "bad_request"),
)


def _envelope(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def register(app: FastAPI) -> None:
    # Os 401/403 vêm da lib: o envelope é o mesmo em todos os serviços.
    register_error_handlers(app)

    @app.exception_handler(DomainError)
    async def handle_domain_error(_request: Request, error: Exception) -> JSONResponse:
        for error_type, status, code in STATUS_BY_ERROR:
            if isinstance(error, error_type):
                return _envelope(status, code, str(error))
        return _envelope(400, "bad_request", str(error))

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation(_request: Request, _error: Exception) -> JSONResponse:
        """O 422 do próprio FastAPI, vestido com o nosso envelope."""
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
