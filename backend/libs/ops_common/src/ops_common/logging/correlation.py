"""Correlation-id: ~15 linhas de middleware que tornam o Graylog utilizável.

O OSB injeta `X-Request-ID`. Cada serviço propaga-o nos logs e nas chamadas seguintes, para que
um pedido seja rastreável ponta a ponta (secção 6 do ARCHITECTURE.md).
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp

HEADER = "X-Request-ID"

_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="-")


def get_correlation_id() -> str:
    return _correlation_id.get()


def set_correlation_id(value: str | None) -> str:
    cid = value or str(uuid.uuid4())
    _correlation_id.set(cid)
    return cid


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Lê o header do OSB (ou gera um), guarda-o no contexto e devolve-o na resposta."""

    def __init__(self, app: ASGIApp, header: str = HEADER) -> None:
        super().__init__(app)
        self.header = header

    async def dispatch(self, request: Request, call_next):
        cid = set_correlation_id(request.headers.get(self.header))
        request.state.correlation_id = cid
        response = await call_next(request)
        response.headers[self.header] = cid
        return response
