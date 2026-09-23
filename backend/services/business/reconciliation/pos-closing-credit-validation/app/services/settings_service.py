"""Caso de uso das definições: ler o prazo de tratamento, e mudá-lo."""

from dataclasses import dataclass
from datetime import datetime

from app.domain.sla import DEFAULT_SLA_DAYS, DEFAULT_WARNING_DAYS, validate_sla
from app.repositories.settings_repository import SettingsRepository


@dataclass(slots=True)
class SlaSettings:
    case_sla_days: int
    case_warning_days: int
    updated_at: datetime | None
    updated_by: str | None


class SettingsService:
    def __init__(self, settings: SettingsRepository) -> None:
        self._settings = settings

    async def get(self) -> SlaSettings:
        row = await self._settings.find()
        if row is None:
            return SlaSettings(
                case_sla_days=DEFAULT_SLA_DAYS,
                case_warning_days=DEFAULT_WARNING_DAYS,
                updated_at=None,
                updated_by=None,
            )
        return SlaSettings(
            case_sla_days=row.case_sla_days,
            case_warning_days=row.case_warning_days,
            updated_at=row.updated_at,
            updated_by=row.updated_by,
        )

    async def save(self, sla_days: int, warning_days: int, updated_by: str | None) -> SlaSettings:
        validate_sla(sla_days, warning_days)
        row = await self._settings.save(sla_days, warning_days, updated_by)
        return SlaSettings(
            case_sla_days=row.case_sla_days,
            case_warning_days=row.case_warning_days,
            updated_at=row.updated_at,
            updated_by=row.updated_by,
        )
