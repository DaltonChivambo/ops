"""Acesso a dados dos casos de divergência."""

from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.vocabulary import CaseStatus, CaseType
from app.infrastructure.tables import PendingCase

# Ordem de leitura: dinheiro errado, o que falta chegar, ambiguidade por desfazer.
# Não é a ordem de declaração do enum.
_TYPE_ORDER = sa.case(
    (PendingCase.type == CaseType.MISMATCH, 0),
    (PendingCase.type == CaseType.MISSING, 1),
    (PendingCase.type == CaseType.DUPLICATED, 2),
)


class CaseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_execution(self, execution_id: str) -> list[PendingCase]:
        # Ver `_TYPE_ORDER`; dentro do tipo, os maiores montantes.
        result = await self._session.execute(
            sa.select(PendingCase)
            .where(PendingCase.execution_id == execution_id)
            .order_by(_TYPE_ORDER, PendingCase.simo_amount.desc())
        )
        return list(result.scalars().all())

    async def list_open_duplicated(self, execution_id: str) -> list[PendingCase]:
        """Os casos de períodos repetidos por tratar — os que se conciliam. Maiores primeiro."""
        result = await self._session.execute(
            sa.select(PendingCase)
            .where(
                PendingCase.execution_id == execution_id,
                PendingCase.type == CaseType.DUPLICATED,
                PendingCase.status != CaseStatus.RESOLVED,
            )
            .order_by(PendingCase.simo_amount.desc())
        )
        return list(result.scalars().all())

    async def find(self, case_id: str) -> PendingCase | None:
        return await self._session.get(PendingCase, case_id)

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
