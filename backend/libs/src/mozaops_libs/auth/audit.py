"""Registo de quem alterou o quê."""

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
