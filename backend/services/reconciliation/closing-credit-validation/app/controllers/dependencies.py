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
from app.services.case_service import CaseService
from app.services.validation_service import ValidationService
from mozaops_libs.auth import READERS, RESOLVERS, WRITERS, Principal

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_execution_repository(session: SessionDep) -> ExecutionRepository:
    return ExecutionRepository(session)


def get_case_repository(session: SessionDep) -> CaseRepository:
    return CaseRepository(session)


ExecutionRepositoryDep = Annotated[ExecutionRepository, Depends(get_execution_repository)]
CaseRepositoryDep = Annotated[CaseRepository, Depends(get_case_repository)]


def get_validation_service(
    executions: ExecutionRepositoryDep, cases: CaseRepositoryDep
) -> ValidationService:
    return ValidationService(executions, cases)


def get_case_service(cases: CaseRepositoryDep, executions: ExecutionRepositoryDep) -> CaseService:
    return CaseService(cases, executions)


ValidationServiceDep = Annotated[ValidationService, Depends(get_validation_service)]
CaseServiceDep = Annotated[CaseService, Depends(get_case_service)]

# ─── Quem está do outro lado, e o que pode fazer ─────────────────────────────
# `require_reader` está no router inteiro (`controllers/router.py`), e não rota
# a rota: assim uma rota acrescentada amanhã nasce fechada, em vez de ficar
# aberta até alguém se lembrar. As outras duas apertam por cima, onde é preciso.
#
# Devolvem o `Principal`, o que deixa a mesma dependência servir de guarda e de
# resposta a «quem está a pedir isto» — sem a rota o pedir duas vezes.
require_reader = auth.require(READERS)
require_writer = auth.require(WRITERS)
require_resolver = auth.require(RESOLVERS)

CurrentUser = Annotated[Principal, Depends(auth.principal)]
Writer = Annotated[Principal, Depends(require_writer)]
Resolver = Annotated[Principal, Depends(require_resolver)]
