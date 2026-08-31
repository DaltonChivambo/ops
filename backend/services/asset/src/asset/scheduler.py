"""Scheduler do Asset Service — manutenção agendada.

    python -m asset.scheduler

APScheduler no mesmo contentor, por enquanto. Separa-se em serviço próprio só se o volume o
justificar (ver `ARCHITECTURE.md` §3.1).
"""

from __future__ import annotations

import asyncio

from asset.core.config import get_settings
from asset.core.logging import configurar

settings = get_settings()


async def main() -> None:
    configurar()
    # TODO: APScheduler — varrer manutenções a vencer e publicar manutencao.vencida
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
