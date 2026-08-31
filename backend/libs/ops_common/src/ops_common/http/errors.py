"""Corpo de erro comum e handlers registáveis.

Um único sítio a mapear exceção → status HTTP. Sem isto aparecem HTTPException espalhados pelos
services/ e o FastAPI volta a infiltrar-se nas camadas de baixo (secção 4 do ARCHITECTURE.md).
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ops_common.logging.correlation import get_correlation_id

logger = logging.getLogger(__name__)


class ErroResposta(BaseModel):
    """Forma única de erro em toda a plataforma — o Angular só tem um formato a tratar."""

    erro: str
    detalhe: str | None = None
    correlation_id: str
    campos: list[dict] | None = None


class ErroDeNegocio(Exception):
    """Base das exceções de domínio de cada serviço.

    Cada serviço define as suas em `core/exceptions.py` herdando daqui e ajustando `status_code`.
    """

    status_code: int = status.HTTP_400_BAD_REQUEST
    erro: str = "erro_de_negocio"

    def __init__(self, detalhe: str | None = None) -> None:
        self.detalhe = detalhe
        super().__init__(detalhe or self.erro)


class NaoEncontrado(ErroDeNegocio):
    status_code = status.HTTP_404_NOT_FOUND
    erro = "nao_encontrado"


class Conflito(ErroDeNegocio):
    status_code = status.HTTP_409_CONFLICT
    erro = "conflito"


class TransicaoInvalida(ErroDeNegocio):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    erro = "transicao_invalida"


def _resposta(status_code: int, erro: str, detalhe: str | None, campos=None) -> JSONResponse:
    corpo = ErroResposta(
        erro=erro, detalhe=detalhe, correlation_id=get_correlation_id(), campos=campos
    )
    return JSONResponse(status_code=status_code, content=corpo.model_dump(exclude_none=True))


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ErroDeNegocio)
    async def _negocio(request: Request, exc: ErroDeNegocio) -> JSONResponse:
        return _resposta(exc.status_code, exc.erro, exc.detalhe)

    @app.exception_handler(RequestValidationError)
    async def _validacao(request: Request, exc: RequestValidationError) -> JSONResponse:
        campos = [
            {"campo": ".".join(str(p) for p in e.get("loc", [])[1:]), "mensagem": e.get("msg")}
            for e in exc.errors()
        ]
        return _resposta(422, "validacao", "Payload inválido", campos)

    @app.exception_handler(HTTPException)
    async def _http(request: Request, exc: HTTPException) -> JSONResponse:
        return _resposta(exc.status_code, "erro_http", str(exc.detail))

    @app.exception_handler(Exception)
    async def _inesperado(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Erro não tratado em %s %s", request.method, request.url.path)
        return _resposta(500, "erro_interno", "Erro interno do servidor")
