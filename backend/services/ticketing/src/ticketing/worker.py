"""Worker de ticketing — processo consumidor de eventos.

    python -m ticketing.worker

Perfil HTTP + publisher + consumidor. Corre em contentor separado do `main.py`, com a mesma imagem.
"""

from __future__ import annotations

import asyncio

from ops_common.messaging import EventConsumer

from ticketing.core.config import get_settings
from ticketing.core.logging import configurar

settings = get_settings()


def build_consumer() -> EventConsumer:
    consumer = EventConsumer(
        url=settings.rabbitmq_url,
        queue=settings.rabbitmq_queue,
        service_name=settings.service_name,
    )
    # TODO: registar handlers — consumer.register("evento.exemplo", handler)
    return consumer


async def main() -> None:
    configurar()
    await build_consumer().run()


if __name__ == "__main__":
    asyncio.run(main())
