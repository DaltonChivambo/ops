"""Notification Service — app factory e lifespan.

Perfil: worker-first.
Esqueleto: os routers da v1 entram em `api/v1/router.py`.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from notification.api import health
from notification.api.error_handler import registar_error_handlers
from notification.api.v1.router import router as router_v1
from notification.core.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # TODO: abrir publisher/consumidor RabbitMQ e o que mais tiver de viver no processo.
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="OPS — Notification Service",
        version="0.1.0",
        lifespan=lifespan,
    )
    registar_error_handlers(app)
    app.include_router(health.router)                        # /health e /ready, fora do /v1
    app.include_router(router_v1, prefix=settings.api_prefix)
    return app


app = create_app()
