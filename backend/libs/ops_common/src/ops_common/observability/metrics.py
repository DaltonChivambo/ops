"""Exportador Prometheus e middleware de métricas HTTP.

Todos os serviços expõem as mesmas séries, com o label `service` — é o que permite ao dashboard
`ops-visao-geral` funcionar sem alterações quando entra um serviço novo.
"""

from __future__ import annotations

import time

from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp

http_requests_total = Counter(
    "http_requests_total",
    "Pedidos HTTP servidos.",
    ["service", "method", "path", "status"],
)
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "Duração dos pedidos HTTP.",
    ["service", "method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
events_published_total = Counter(
    "ops_events_published_total",
    "Eventos publicados no barramento.",
    ["service", "event_name"],
)
events_consumed_total = Counter(
    "ops_events_consumed_total",
    "Eventos consumidos do barramento.",
    ["service", "event_name", "resultado"],
)
service_info = Gauge("ops_service_up", "1 enquanto o serviço estiver a servir.", ["service"])


class MetricsMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, service_name: str) -> None:
        super().__init__(app)
        self.service_name = service_name

    async def dispatch(self, request: Request, call_next):
        # A rota (template) e não o caminho concreto: senão cada id vira uma série nova.
        inicio = time.perf_counter()
        response = await call_next(request)
        rota = request.scope.get("route")
        path = getattr(rota, "path", request.url.path)
        if path != "/metrics":
            duracao = time.perf_counter() - inicio
            http_requests_total.labels(
                self.service_name, request.method, path, str(response.status_code)
            ).inc()
            http_request_duration_seconds.labels(
                self.service_name, request.method, path
            ).observe(duracao)
        return response


def setup_metrics(app: FastAPI, service_name: str) -> None:
    """Regista o middleware e o endpoint `/metrics` (fora do `/api/v1`)."""
    app.add_middleware(MetricsMiddleware, service_name=service_name)
    service_info.labels(service_name).set(1)

    @app.get("/metrics", include_in_schema=False)
    def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
