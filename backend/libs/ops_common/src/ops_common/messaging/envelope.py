"""Envelope de evento — o contrato do barramento.

Todos os eventos da plataforma têm a mesma forma exterior; o que varia é o `data`, opaco para
quem transporta. O `correlation_id` viaja no envelope: é o que liga um evento assíncrono ao
pedido HTTP que o originou, no Graylog.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def _agora() -> datetime:
    return datetime.now(timezone.utc)


class EventEnvelope(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_name: str                      # routing key: ativo.criado, ticket.aberto, ...
    event_version: int = 1
    occurred_at: datetime = Field(default_factory=_agora)
    producer: str                        # nome do serviço que publicou
    correlation_id: str = "-"
    data: dict[str, Any] = {}

    def to_bytes(self) -> bytes:
        return self.model_dump_json().encode("utf-8")

    @classmethod
    def from_bytes(cls, raw: bytes) -> "EventEnvelope":
        return cls.model_validate_json(raw)
