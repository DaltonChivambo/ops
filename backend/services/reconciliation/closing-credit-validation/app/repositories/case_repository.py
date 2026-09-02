"""Acesso a dados dos casos de divergência.

Os casos são criados pelo `ExecutionRepository`, junto com a execução a que
pertencem — a `Execution` é a raiz do agregado. Daqui para a frente é o
operador que lhes mexe, um a um, e é isso que este repositório serve.

Como o outro: a sessão vem de fora e nunca se cria aqui.
"""

from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.tables import PendingCase


class CaseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_execution(self, execution_id: str) -> list[PendingCase]:
        # A ordem vem da declaração do enum `CaseType` (missing, mismatch): os
        # não-creditados aparecem primeiro. Dentro do tipo, os maiores montantes.
        result = await self._session.execute(
            sa.select(PendingCase)
            .where(PendingCase.execution_id == execution_id)
            .order_by(PendingCase.type.asc(), PendingCase.simo_amount.desc())
        )
        return list(result.scalars().all())

    async def find_by_key(self, execution_id: str, key: str) -> PendingCase | None:
        result = await self._session.execute(
            sa.select(PendingCase).where(
                PendingCase.execution_id == execution_id, PendingCase.key == key
            )
        )
        return result.scalar_one_or_none()

    async def update(self, case_id: str, patch: dict[str, Any]) -> PendingCase | None:
        case = await self._session.get(PendingCase, case_id)
        if case is None:
            return None
        for field, value in patch.items():
            setattr(case, field, value)
        await self._session.flush()
        return case

    async def count_by_status(self, execution_id: str) -> dict[str, int]:
        result = await self._session.execute(
            sa.select(PendingCase.status, sa.func.count())
            .where(PendingCase.execution_id == execution_id)
            .group_by(PendingCase.status)
        )
        return {status: total for status, total in result.all()}
