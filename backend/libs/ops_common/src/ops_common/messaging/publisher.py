"""Publisher RabbitMQ (aio-pika), com ligação robusta e mensagens persistentes.

Sem padrão outbox: está adiado com gatilho definido — entra quando a primeira perda de evento
custar mais que a tabela e o poller extra (secção 9 do ARCHITECTURE.md).
"""

from __future__ import annotations

import logging

import aio_pika
from aio_pika.abc import AbstractRobustConnection

from ops_common.logging.correlation import get_correlation_id
from ops_common.messaging.envelope import EventEnvelope
from ops_common.observability.metrics import events_published_total

logger = logging.getLogger(__name__)


class EventPublisher:
    """Ligação partilhada pelo processo, aberta no lifespan e fechada no shutdown."""

    def __init__(self, url: str, exchange: str, service_name: str) -> None:
        self.url = url
        self.exchange_name = exchange
        self.service_name = service_name
        self._connection: AbstractRobustConnection | None = None
        self._channel: aio_pika.abc.AbstractChannel | None = None
        self._exchange: aio_pika.abc.AbstractExchange | None = None

    async def connect(self) -> None:
        if self._connection is not None and not self._connection.is_closed:
            return
        self._connection = await aio_pika.connect_robust(self.url)
        self._channel = await self._connection.channel(publisher_confirms=True)
        self._exchange = await self._channel.declare_exchange(
            self.exchange_name, aio_pika.ExchangeType.TOPIC, durable=True
        )
        logger.info("Publisher ligado a %s (exchange %s)", self.url, self.exchange_name)

    async def close(self) -> None:
        if self._connection is not None and not self._connection.is_closed:
            await self._connection.close()
        self._connection = self._channel = self._exchange = None

    async def publish(self, event_name: str, data: dict, event_version: int = 1) -> EventEnvelope:
        if self._exchange is None:
            await self.connect()
        assert self._exchange is not None

        envelope = EventEnvelope(
            event_name=event_name,
            event_version=event_version,
            producer=self.service_name,
            correlation_id=get_correlation_id(),
            data=data,
        )
        message = aio_pika.Message(
            body=envelope.to_bytes(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            message_id=envelope.event_id,
            correlation_id=envelope.correlation_id,
            type=event_name,
        )
        await self._exchange.publish(message, routing_key=event_name)
        events_published_total.labels(self.service_name, event_name).inc()
        logger.info(
            "Evento publicado: %s",
            event_name,
            extra={"event_name": event_name, "event_id": envelope.event_id},
        )
        return envelope
