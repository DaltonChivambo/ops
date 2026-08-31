"""Eventos publicados por asset: [ativo.criado, ativo.actualizado, manutencao.agendada].

    publisher = EventPublisher(url, exchange, service_name)
    await publisher.publish("evento.exemplo", {...})
"""

from __future__ import annotations

from ops_common.messaging import EventPublisher

__all__ = ["EventPublisher"]
