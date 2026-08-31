"""Camada de acesso a dados — a ÚNICA que fala com a base de dados.

Porte de `repositories.py` do MozaOps v1 (Prisma → SQLAlchemy async). Nenhuma
outra camada importa `sqlalchemy`: assim a troca de ORM fica contida aqui.
"""
import uuid
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from .domain.models import ReconciliationResult
from .models import ClosingDetail, CreditMovement, Execution, PendingCase
from .pagination import Page

# O Postgres aceita inserções grandes, mas lotes desta ordem mantêm a memória
# estável nas ~18k linhas de uma execução real.
INSERT_BATCH = 5_000

VALIDATION_STATES = frozenset(("match", "mismatch", "missing", "zero", "duplicated"))


async def create_execution(
    session: AsyncSession,
    result: ReconciliationResult,
    files: dict[str, str],
    summary: dict,
) -> str:
    """Persiste execução + detalhes + movimentos + casos numa única transacção."""
    execution_id = str(uuid.uuid4())
    session.add(
        Execution(
            id=execution_id,
            periodStart=result.periodStart,
            periodEnd=result.periodEnd,
            reportName=result.reportName,
            posListFile=files["posList"],
            simoClosingsFile=files["simoClosings"],
            bankaCreditsFile=files["bankaCredits"],
            summary=summary,
        )
    )
    await session.flush()

    details = [
        {
            "id": str(uuid.uuid4()),
            "executionId": execution_id,
            "posId": detail.posId,
            "merchant": detail.merchant,
            "accountNumber": detail.accountNumber,
            "period": detail.period,
            "key": detail.key,
            "simoClosingDate": detail.simoClosingDate,
            "operationNumber": detail.operationNumber,
            "simoClosingTotal": detail.simoClosingTotal,
            "simoKeyTotal": detail.simoKeyTotal,
            "closingDescription": detail.closingDescription,
            "bankaCreditDate": detail.bankaCreditDate,
            "bankaClosingTotal": detail.bankaClosingTotal,
            "closingType": detail.closingType,
            "validation": detail.validation,
            "difference": detail.difference,
        }
        for detail in result.details
    ]
    for start in range(0, len(details), INSERT_BATCH):
        batch = details[start : start + INSERT_BATCH]
        if batch:
            await session.execute(sa.insert(ClosingDetail), batch)

    # Uma linha por movimento do Banka (~18k, a par dos detalhes): é o que
    # permite abrir um fecho e ver as parcelas do crédito da chave.
    movements = [
        {
            "id": str(uuid.uuid4()),
            "executionId": execution_id,
            "key": movement.key,
            "movementDate": movement.date,
            "amount": movement.amount,
            "description": movement.description,
        }
        for movement in result.movements
    ]
    for start in range(0, len(movements), INSERT_BATCH):
        batch = movements[start : start + INSERT_BATCH]
        if batch:
            await session.execute(sa.insert(CreditMovement), batch)

    cases = [
        {
            "id": str(uuid.uuid4()),
            "executionId": execution_id,
            "key": case.key,
            "posId": case.posId,
            "period": case.period,
            "merchant": case.merchant,
            "accountNumber": case.accountNumber,
            "simoAmount": case.simoAmount,
            "bankaAmount": case.bankaAmount,
            "type": case.type,
        }
        for case in result.cases
    ]
    if cases:
        await session.execute(sa.insert(PendingCase), cases)

    return execution_id


async def find_latest_execution(session: AsyncSession) -> Execution | None:
    result = await session.execute(sa.select(Execution).order_by(Execution.executedAt.desc()).limit(1))
    return result.scalar_one_or_none()


async def find_execution(session: AsyncSession, execution_id: str) -> Execution | None:
    return await session.get(Execution, execution_id)


async def list_cases(session: AsyncSession, execution_id: str) -> list[PendingCase]:
    # A ordem vem da declaração do enum `CaseType` (missing, mismatch): os
    # não-creditados aparecem primeiro. Dentro do tipo, os maiores montantes.
    result = await session.execute(
        sa.select(PendingCase)
        .where(PendingCase.executionId == execution_id)
        .order_by(PendingCase.type.asc(), PendingCase.simoAmount.desc())
    )
    return list(result.scalars().all())


async def list_details(
    session: AsyncSession,
    execution_id: str,
    page: Page,
    validation: str | None = None,
    search: str | None = None,
) -> tuple[list[ClosingDetail], int]:
    where = _details_where(execution_id, validation, search)
    items_result = await session.execute(
        sa.select(ClosingDetail)
        .where(*where)
        # A ordem vem da declaração do enum `Validation` no schema, lida ao
        # contrário: duplicados · não creditados · incorrectos · conferem ·
        # zerados. Primeiro o que exige trabalho, no fim os zerados, que não
        # pedem nada a ninguém. Dentro da chave ordena-se por data, para as
        # linhas da mesma chave ficarem contíguas e a tabela as poder agrupar.
        .order_by(
            ClosingDetail.validation.desc(),
            ClosingDetail.posId.asc(),
            ClosingDetail.period.asc(),
            ClosingDetail.simoClosingDate.asc(),
        )
        .offset(page.skip)
        .limit(page.take)
    )
    total_result = await session.execute(
        sa.select(sa.func.count()).select_from(ClosingDetail).where(*where)
    )
    return list(items_result.scalars().all()), total_result.scalar_one()


async def list_all_details(session: AsyncSession, execution_id: str) -> list[ClosingDetail]:
    """Todos os detalhes da execução, na ordem natural do relatório."""
    result = await session.execute(
        sa.select(ClosingDetail)
        .where(ClosingDetail.executionId == execution_id)
        .order_by(ClosingDetail.posId.asc(), ClosingDetail.period.asc())
    )
    return list(result.scalars().all())


async def list_details_by_key(
    session: AsyncSession, execution_id: str, key: str
) -> list[ClosingDetail]:
    """Os fechos SIMO de uma chave, na ordem em que o operador os lê."""
    result = await session.execute(
        sa.select(ClosingDetail)
        .where(ClosingDetail.executionId == execution_id, ClosingDetail.key == key)
        .order_by(ClosingDetail.simoClosingDate.asc(), ClosingDetail.operationNumber.asc())
    )
    return list(result.scalars().all())


async def list_movements_by_key(
    session: AsyncSession, execution_id: str, key: str
) -> list[CreditMovement]:
    """Os movimentos de crédito do Banka de uma chave, por data."""
    result = await session.execute(
        sa.select(CreditMovement)
        .where(CreditMovement.executionId == execution_id, CreditMovement.key == key)
        .order_by(CreditMovement.movementDate.asc())
    )
    return list(result.scalars().all())


async def find_case_by_key(
    session: AsyncSession, execution_id: str, key: str
) -> PendingCase | None:
    result = await session.execute(
        sa.select(PendingCase).where(
            PendingCase.executionId == execution_id, PendingCase.key == key
        )
    )
    return result.scalar_one_or_none()


async def count_details_by_validation(
    session: AsyncSession, execution_id: str, search: str | None = None
) -> dict[str, int]:
    """Contagens para os chips — sobre TODAS as linhas da execução, não da página."""
    counts = {"all": 0, "match": 0, "mismatch": 0, "missing": 0, "zero": 0, "duplicated": 0}
    where = _details_where(execution_id, None, search)
    result = await session.execute(
        sa.select(ClosingDetail.validation, sa.func.count())
        .where(*where)
        .group_by(ClosingDetail.validation)
    )
    for validation, total in result.all():
        counts[validation] = total
        counts["all"] += total
    return counts


async def update_case(
    session: AsyncSession, case_id: str, patch: dict[str, Any]
) -> PendingCase | None:
    case = await session.get(PendingCase, case_id)
    if case is None:
        return None
    for field, value in patch.items():
        setattr(case, field, value)
    await session.flush()
    return case


async def count_cases_by_status(session: AsyncSession, execution_id: str) -> dict[str, int]:
    result = await session.execute(
        sa.select(PendingCase.status, sa.func.count())
        .where(PendingCase.executionId == execution_id)
        .group_by(PendingCase.status)
    )
    return dict(result.all())


async def save_summary(session: AsyncSession, execution_id: str, summary: dict) -> None:
    await session.execute(
        sa.update(Execution).where(Execution.id == execution_id).values(summary=summary)
    )


def _details_where(
    execution_id: str, validation: str | None, search: str | None
) -> list[Any]:
    conditions: list[Any] = [ClosingDetail.executionId == execution_id]
    if validation:
        # Lista de estados a mostrar, separada por vírgulas. Tokens desconhecidos
        # caem fora, por isso a selecção vazia (o cliente manda «nenhum») não
        # devolve nada. Parâmetro ausente OU vazio não filtra: `?validation=` a
        # devolver zero linhas seria uma armadilha para quem chama a API à mão.
        wanted = [token for token in validation.split(",") if token in VALIDATION_STATES]
        conditions.append(ClosingDetail.validation.in_(wanted))
    if search:
        term = search.strip()
        if term:
            pattern = f"%{term}%"
            conditions.append(
                sa.or_(
                    ClosingDetail.posId.ilike(pattern),
                    ClosingDetail.merchant.ilike(pattern),
                    ClosingDetail.accountNumber.ilike(pattern),
                )
            )
    return conditions
