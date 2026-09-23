"""Acesso às definições do serviço — a linha única da tabela `setting`."""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.tables import Setting

# A tabela tem uma `CHECK (id = 1)`: não há segunda linha para procurar.
ROW_ID = 1


class SettingsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find(self) -> Setting | None:
        return await self._session.get(Setting, ROW_ID)

    async def save(self, sla_days: int, warning_days: int, updated_by: str | None) -> Setting:
        """Grava por cima, criando a linha se a base ainda não a tiver."""
        row = await self._session.get(Setting, ROW_ID)
        if row is None:
            row = Setting(id=ROW_ID)
            self._session.add(row)
        row.case_sla_days = sla_days
        row.case_warning_days = warning_days
        # UTC sem fuso: a coluna é `DateTime` simples.
        row.updated_at = datetime.now(UTC).replace(tzinfo=None)
        row.updated_by = updated_by
        await self._session.flush()
        return row
