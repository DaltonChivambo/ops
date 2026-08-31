"""Eventos consumidos por ticketing: [ativo.criado, ativo.actualizado, pedido.decidido].

Um handler por evento, registados no `EventConsumer` de `ops_common.messaging`.
Ack só depois do handler correr sem exceção; falha => DLQ, nunca ciclo infinito.
"""

from __future__ import annotations

from ops_common.messaging import EventConsumer, EventEnvelope

__all__ = ["EventConsumer", "EventEnvelope"]
