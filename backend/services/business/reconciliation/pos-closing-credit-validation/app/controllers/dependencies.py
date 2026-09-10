"""A cablagem do pedido: sessão → repositórios → serviços.

É aqui, e só aqui, que se diz quem recebe o quê. O `Depends()` do FastAPI faz de
contentor de injecção — não há nem é preciso outro.

Vale também como fronteira dos testes: substituir `get_validation_service` por
um duplo dá um cliente HTTP sem base de dados nenhuma.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.auth import auth
from app.infrastructure.database import get_session
from app.repositories.case_repository import CaseRepository
from app.repositories.execution_repository import ExecutionRepository
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


ExecutionRepositoryDep = Annotated[ExecutionRepository, Depends(get_execution_repository)]
CaseRepositoryDep = Annotated[CaseRepository, Depends(get_case_repository)]
SettingsRepositoryDep = Annotated[SettingsRepository, Depends(get_settings_repository)]


def get_validation_service(
    executions: ExecutionRepositoryDep, cases: CaseRepositoryDep
) -> ValidationService:
    return ValidationService(executions, cases)


def get_case_service(cases: CaseRepositoryDep, executions: ExecutionRepositoryDep) -> CaseService:
    return CaseService(cases, executions)


def get_settings_service(settings_repository: SettingsRepositoryDep) -> SettingsService:
    return SettingsService(settings_repository)


ValidationServiceDep = Annotated[ValidationService, Depends(get_validation_service)]
CaseServiceDep = Annotated[CaseService, Depends(get_case_service)]
SettingsServiceDep = Annotated[SettingsService, Depends(get_settings_service)]

# ─── Quem está do outro lado ─────────────────────────────────────────────────
# Uma guarda só, no router inteiro (`controllers/router.py`), e não rota a
# rota: assim uma rota acrescentada amanhã nasce fechada, em vez de ficar
# aberta até alguém se lembrar.
#
# É uma só porque dentro da área não há graus — quem entra, faz tudo o que a
# automação faz. O dia em que voltar a haver um acto reservado a alguém, é
# aqui que nasce a segunda.
#
# Devolve o `Principal`, o que deixa a mesma dependência servir de guarda e de
# resposta a «quem está a pedir isto» — sem a rota o pedir duas vezes.
require_area = auth.require_area(settings.auth_service_area)

CurrentUser = Annotated[Principal, Depends(auth.principal)]
