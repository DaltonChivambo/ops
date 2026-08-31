"""Entrada do serviço `closing-reconciliation`.

Sem Keycloak e sem CORS por agora — ver a nota de âmbito no plano desta
funcionalidade. Todas as rotas ficam abertas; fechar isto é trabalho do M6+.
"""
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .errors import ApiError
from .routes import router

logger = logging.getLogger("closing_reconciliation")

app = FastAPI(title="MozaOps — closing-reconciliation")

app.include_router(router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(ApiError)
async def handle_api_error(_request: Request, error: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status, content={"error": {"code": error.code, "message": error.message}}
    )


@app.exception_handler(Exception)
async def handle_unexpected(_request: Request, error: Exception) -> JSONResponse:
    logger.exception("Erro inesperado", exc_info=error)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_error",
                "message": "Ocorreu um erro inesperado no servidor. Tente novamente.",
            }
        },
    )
