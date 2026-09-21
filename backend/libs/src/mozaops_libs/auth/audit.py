"""Registo de quem alterou o quê.

Só as escritas: uma leitura não muda nada, e registá-las afogava o que importa.

Existe porque nada mais o faz. O access log do Traefik guarda apenas respostas
400-599 e descarta o `Authorization`, e os serviços não instrumentam tracing —
uma execução corrida com sucesso não deixava rasto em lado nenhum.
"""

import logging
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

from mozaops_libs.auth.access import SAFE_METHODS

logger = logging.getLogger("audit")

ANONYMOUS = "anónimo"


def register_audit(app: FastAPI) -> None:
    @app.middleware("http")
    async def record_writes(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)

        if request.method.upper() not in SAFE_METHODS:
            principal = getattr(request.state, "principal", None)
            logger.info(
                "%s %s %s por %s (%s)",
                request.method,
                request.url.path,
                response.status_code,
                principal.username if principal else ANONYMOUS,
                principal.subject if principal else ANONYMOUS,
            )

        return response
