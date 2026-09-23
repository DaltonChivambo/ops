"""Acesso a dados da conciliação fecho a fecho."""

from collections.abc import Collection, Sequence

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.matching import Match
from app.infrastructure.tables import ClosingMatch


class MatchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_key(self, execution_id: str, key: str) -> list[ClosingMatch]:
        return await self.list_by_keys(execution_id, [key])

    async def list_by_keys(self, execution_id: str, keys: Collection[str]) -> list[ClosingMatch]:
        if not keys:
            return []
        result = await self._session.execute(
            sa.select(ClosingMatch)
            .where(ClosingMatch.execution_id == execution_id, ClosingMatch.key.in_(keys))
            .order_by(ClosingMatch.key.asc(), ClosingMatch.matched_at.asc())
        )
        return list(result.scalars().all())

    async def replace_for_key(
        self,
        execution_id: str,
        key: str,
        matches: Sequence[Match],
        matched_by: str | None,
    ) -> list[ClosingMatch]:
        await self._session.execute(
            sa.delete(ClosingMatch).where(
                ClosingMatch.execution_id == execution_id, ClosingMatch.key == key
            )
        )
        # O delete tem de chegar à base antes dos inserts, por causa das `unique`.
        await self._session.flush()
        rows = [
            ClosingMatch(
                execution_id=execution_id,
                key=key,
                closing_id=match.closing_id,
                movement_id=match.movement_id,
                matched_by=matched_by,
            )
            for match in matches
        ]
        self._session.add_all(rows)
        await self._session.flush()
        return rows
