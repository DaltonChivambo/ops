"""A cablagem do pedido: sessão → repositórios → serviços."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.auth import auth
from app.infrastructure.database import get_session
from app.repositories.case_repository import CaseRepository
from app.repositories.execution_repository import ExecutionRepository
from app.repositories.match_repository import MatchRepository
from app.repositories.settings_repository import SettingsRepository
from app.services.case_service import CaseService
from app.services.settings_service import SettingsService
from app.services.validation_service import ValidationService
from app.settings import settings
from mozaops_libs.auth import Principal

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_execution_repository(session: SessionDep) -> ExecutionRepository:
    return ExecutionRepository(session)


def get_case_repository(session: SessionDep) -> CaseRepository:
    return CaseRepository(session)


def get_settings_repository(session: SessionDep) -> SettingsRepository:
    return SettingsRepository(session)


def get_match_repository(session: SessionDep) -> MatchRepository:
    return MatchRepository(session)


ExecutionRepositoryDep = Annotated[ExecutionRepository, Depends(get_execution_repository)]
CaseRepositoryDep = Annotated[CaseRepository, Depends(get_case_repository)]
SettingsRepositoryDep = Annotated[SettingsRepository, Depends(get_settings_repository)]
MatchRepositoryDep = Annotated[MatchRepository, Depends(get_match_repository)]


def get_validation_service(
    executions: ExecutionRepositoryDep, cases: CaseRepositoryDep, matches: MatchRepositoryDep
) -> ValidationService:
    return ValidationService(executions, cases, matches)


def get_case_service(
    cases: CaseRepositoryDep, executions: ExecutionRepositoryDep, matches: MatchRepositoryDep
) -> CaseService:
    return CaseService(cases, executions, matches)


def get_settings_service(settings_repository: SettingsRepositoryDep) -> SettingsService:
    return SettingsService(settings_repository)


ValidationServiceDep = Annotated[ValidationService, Depends(get_validation_service)]
CaseServiceDep = Annotated[CaseService, Depends(get_case_service)]
SettingsServiceDep = Annotated[SettingsService, Depends(get_settings_service)]

# ─── Quem está do outro lado ─────────────────────────────────────────────────
# Uma guarda só, no router inteiro (`controllers/router.py`), e não rota a rota.
# Devolve o `Principal`, para servir de guarda e de resposta a quem pede.
require_access = auth.require_access(settings.auth_service_id, settings.auth_service_area)

CurrentUser = Annotated[Principal, Depends(auth.principal)]
