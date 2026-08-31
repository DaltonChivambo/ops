"""Montagem comum de um serviço FastAPI.

Tudo o que os seis serviços fazem exatamente da mesma maneira vive aqui: logging, correlation-id,
métricas, CORS e error handlers. O `main.py` de cada serviço fica com o que é seu — o lifespan e
os routers.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ops_common.config import BaseServiceSettings
from ops_common.http.errors import register_error_handlers
from ops_common.logging.correlation import CorrelationIdMiddleware
from ops_common.logging.setup import setup_logging
from ops_common.observability.metrics import setup_metrics


def setup_service(app: FastAPI, settings: BaseServiceSettings) -> FastAPI:
    setup_logging(
        service_name=settings.service_name,
        level=settings.log_level,
        graylog_host=settings.graylog_host,
        graylog_port=settings.graylog_port,
    )

    # A ordem importa: o correlation-id tem de ser o middleware mais exterior, para que já
    # esteja no contexto quando qualquer outro escrever uma linha de log.
    if settings.metrics_enabled:
        setup_metrics(app, settings.service_name)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(CorrelationIdMiddleware)

    register_error_handlers(app)
    return app
