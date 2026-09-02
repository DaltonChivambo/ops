"""Excepção de domínio → resposta HTTP. O único sítio que conhece os dois lados.

O domínio levanta o que correu mal no seu próprio vocabulário; é esta tabela que
decide com que estado isso sai. Manter o mapeamento aqui é o que permite ao
adaptador de Excel levantar um erro de negócio sem importar nada de HTTP.

O envelope `{"error": {"code", "message"}}` é contrato: o `error.interceptor.ts`
do SPA depende desta forma exacta para transformar a resposta num `ApiError` com
mensagem para mostrar ao operador.
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

logger = logging.getLogger("closing_credit_validation")

# Percorrido pela MRO da excepção, do mais específico para o mais geral: uma
# subclasse nova de `BusinessRuleError` cai no 422 sem se tocar aqui.
STATUS_BY_ERROR: tuple[tuple[type[DomainError], int, str], ...] = (
    (NotFoundError, 404, "not_found"),
    # Antes do `BusinessRuleError`, de quem é subclasse: um ficheiro grande
    # demais tem estado próprio, e o 413 diz ao operador o que aconteceu.
    (UploadTooLargeError, 413, "payload_too_large"),
    (BusinessRuleError, 422, "business_rule"),
    (NothingToUpdateError, 400, "bad_request"),
    (DomainError, 400, "bad_request"),
)


def _envelope(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def register(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(_request: Request, error: Exception) -> JSONResponse:
        for tipo, status, code in STATUS_BY_ERROR:
            if isinstance(error, tipo):
                return _envelope(status, code, str(error))
        return _envelope(400, "bad_request", str(error))

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation(_request: Request, _error: Exception) -> JSONResponse:
        """O 422 do próprio FastAPI, vestido com o nosso envelope.

        Sem isto, um `?page=abc` ou um corpo que não é JSON devolviam o
        `{"detail": [...]}` do FastAPI — a única resposta do serviço que o
        `error.interceptor.ts` do SPA não sabia ler, e que caía na mensagem
        genérica de «erro inesperado».
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
