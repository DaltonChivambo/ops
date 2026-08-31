"""Handler GELF sobre UDP para o Graylog.

Deliberadamente sem dependência externa: o formato GELF são ~40 linhas e assim controlamos os
campos adicionais (`_correlation_id`, `_service`, `_event_name`) que a pesquisa no Graylog usa.
"""

from __future__ import annotations

import json
import logging
import socket
import time
import zlib

# GELF: 1=alert ... 7=debug (syslog). Mapeamento a partir dos níveis do logging.
_SYSLOG_LEVEL = {
    logging.CRITICAL: 2,
    logging.ERROR: 3,
    logging.WARNING: 4,
    logging.INFO: 6,
    logging.DEBUG: 7,
}

_RESERVED = {
    "args", "asctime", "created", "exc_info", "exc_text", "filename", "funcName",
    "levelname", "levelno", "lineno", "module", "msecs", "message", "msg", "name",
    "pathname", "process", "processName", "relativeCreated", "stack_info",
    "thread", "threadName", "taskName",
}


class GelfUdpHandler(logging.Handler):
    """Envia cada registo como um datagrama GELF comprimido."""

    def __init__(self, host: str, port: int = 12201, service: str = "servico") -> None:
        super().__init__()
        self.host = host
        self.port = port
        self.service = service
        self.source = socket.gethostname()
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            payload = self._to_gelf(record)
            self._sock.sendto(zlib.compress(payload), (self.host, self.port))
        except Exception:  # noqa: BLE001 - logging nunca derruba a aplicação
            self.handleError(record)

    def _to_gelf(self, record: logging.LogRecord) -> bytes:
        from ops_common.logging.correlation import get_correlation_id

        message = record.getMessage()
        gelf: dict[str, object] = {
            "version": "1.1",
            "host": self.source,
            "short_message": message[:250],
            "full_message": message,
            "timestamp": time.time(),
            "level": _SYSLOG_LEVEL.get(record.levelno, 6),
            "_service": self.service,
            "_logger": record.name,
            "_correlation_id": get_correlation_id(),
            "_file": record.pathname,
            "_line": record.lineno,
        }
        if record.exc_info:
            gelf["full_message"] = self.format(record)

        # Campos extra passados em logger.info("...", extra={"event_name": ...})
        for key, value in record.__dict__.items():
            if key in _RESERVED or key.startswith("_"):
                continue
            if key in {"correlation_id", "service"}:
                continue
            gelf[f"_{key}"] = value if isinstance(value, (str, int, float, bool)) else str(value)

        return json.dumps(gelf, default=str).encode("utf-8")

    def close(self) -> None:
        try:
            self._sock.close()
        finally:
            super().close()
