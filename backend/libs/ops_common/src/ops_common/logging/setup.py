"""Configuração de logging de um serviço: consola legível + GELF para o Graylog."""

from __future__ import annotations

import logging
import sys

from ops_common.logging.correlation import get_correlation_id
from ops_common.logging.gelf import GelfUdpHandler


class _CorrelationFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id()
        return True


def setup_logging(
    service_name: str,
    level: str = "INFO",
    graylog_host: str | None = None,
    graylog_port: int = 12201,
) -> None:
    root = logging.getLogger()
    root.setLevel(level.upper())
    for handler in list(root.handlers):
        root.removeHandler(handler)

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)-8s [%(correlation_id)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    console.addFilter(_CorrelationFilter())
    root.addHandler(console)

    if graylog_host:
        gelf = GelfUdpHandler(graylog_host, graylog_port, service=service_name)
        gelf.addFilter(_CorrelationFilter())
        root.addHandler(gelf)

    # O uvicorn traz handlers próprios; sem isto, cada linha aparece duas vezes.
    for noisy in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(noisy).handlers = []
        logging.getLogger(noisy).propagate = True

    logging.getLogger("aio_pika").setLevel("WARNING")
    logging.getLogger("aiormq").setLevel("WARNING")
