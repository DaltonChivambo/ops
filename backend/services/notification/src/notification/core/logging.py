"""Logging do serviço: GELF → Graylog, com correlation-id em cada linha."""

from __future__ import annotations

import logging

from ops_common.logging import setup_logging

from notification.core.config import get_settings


def configurar() -> None:
    settings = get_settings()
    setup_logging(
        service_name=settings.service_name,
        level=settings.log_level,
        graylog_host=settings.graylog_host,
        graylog_port=settings.graylog_port,
    )


def get_logger(nome: str) -> logging.Logger:
    return logging.getLogger(nome)
