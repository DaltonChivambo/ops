"""Consumidor RabbitMQ: um handler por event_name, ack manual, DLQ para o resto.

Regras de sobrevivência do worker:
  * ack só depois de o handler ter corrido sem exceção — parar o worker não perde mensagens;
  * exceção no handler => reject(requeue=False) => a mensagem vai para a DLQ, em vez de ficar
    em ciclo infinito a bloquear a fila;
  * evento sem handler registado é confirmado e ignorado (a fila liga com routing key `#`,
    portanto chegam eventos de todos os serviços).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

import aio_pika
from aio_pika.abc import AbstractIncomingMessage

from ops_common.logging.correlation import set_correlation_id
from ops_common.messaging.envelope import EventEnvelope
from ops_common.observability.metrics import events_consumed_total

logger = logging.getLogger(__name__)

Handler = Callable[[EventEnvelope], Awaitable[None]]


class EventConsumer:
    def __init__(self, url: str, queue: str, service_name: str, prefetch: int = 10) -> None:
        self.url = url
        self.queue_name = queue
        self.service_name = service_name
        self.prefetch = prefetch
        self._handlers: dict[str, Handler] = {}
        self._stop = asyncio.Event()

    def on(self, event_name: str) -> Callable[[Handler], Handler]:
        """Decorador de registo: @consumer.on("ativo.criado")."""

        def decorator(handler: Handler) -> Handler:
            self._handlers[event_name] = handler
            return handler

        return decorator

    def register(self, event_name: str, handler: Handler) -> None:
        self._handlers[event_name] = handler

    async def _processar(self, message: AbstractIncomingMessage) -> None:
        try:
            envelope = EventEnvelope.from_bytes(message.body)
        except Exception:
            logger.exception("Mensagem ilegível — para a DLQ")
            await message.reject(requeue=False)
            return

        set_correlation_id(envelope.correlation_id)
        handler = self._handlers.get(envelope.event_name)
        if handler is None:
            await message.ack()
            return

        try:
            await handler(envelope)
        except Exception:
            events_consumed_total.labels(self.service_name, envelope.event_name, "erro").inc()
            logger.exception(
                "Falha a processar %s — para a DLQ",
                envelope.event_name,
                extra={"event_name": envelope.event_name, "event_id": envelope.event_id},
            )
            await message.reject(requeue=False)
            return

        events_consumed_total.labels(self.service_name, envelope.event_name, "ok").inc()
        await message.ack()

    async def run(self) -> None:
        connection = await aio_pika.connect_robust(self.url)
        async with connection:
            channel = await connection.channel()
            await channel.set_qos(prefetch_count=self.prefetch)
            queue = await channel.get_queue(self.queue_name, ensure=True)
            logger.info(
                "Consumidor à escuta em %s: %s",
                self.queue_name,
                ", ".join(sorted(self._handlers)) or "(nenhum handler)",
            )
            await queue.consume(self._processar)
            await self._stop.wait()

    def stop(self) -> None:
        self._stop.set()
