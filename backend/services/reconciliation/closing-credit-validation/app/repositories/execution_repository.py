"""Acesso a dados da execução e de tudo o que lhe pertence.

Porte de `repositories.py` do MozaOps v1 (Prisma → SQLAlchemy async). Esta
camada e a `CaseRepository` são as ÚNICAS que importam `sqlalchemy`: é isso que
mantém a troca de ORM contida aqui.

**A sessão vem de fora, e nunca se cria aqui.** É a regra que substitui uma
unit of work: quem abre a sessão é o `Depends` do pedido, o repositório apenas a
recebe, e é por isso que tudo o que corre num pedido partilha a transacção.
"""

import uuid
from collections.abc import Mapping
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import ReconciliationResult
from app.domain.vocabulary import UploadSlot, Validation
from app.infrastructure.tables import ClosingDetail, CreditMovement, Execution, PendingCase
from app.pagination import Page

# O Postgres aceita inserções grandes, mas lotes desta ordem mantêm a memória
# estável nas ~18k linhas de uma execução real.
INSERT_BATCH = 5_000

VALIDATION_STATES = frozenset(Validation)


class ExecutionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        result: ReconciliationResult,
        files: Mapping[UploadSlot, str],
        summary: dict[str, Any],
    ) -> str:
        """Persiste execução + detalhes + movimentos + casos numa única transacção.

        Os casos entram por aqui e não pelo `CaseRepository` de propósito: a
        `Execution` é a raiz do agregado, e partir esta escrita em duas deixava
        a porta aberta a uma execução gravada sem os casos dela.
        """
        execution_id = str(uuid.uuid4())
        self._session.add(
            Execution(
                id=execution_id,
                periodStart=result.periodStart,
                periodEnd=result.periodEnd,
                reportName=result.reportName,
                posListFile=files[UploadSlot.POS_LIST],
                simoClosingsFile=files[UploadSlot.SIMO_CLOSINGS],
                bankaCreditsFile=files[UploadSlot.BANKA_CREDITS],
                summary=summary,
            )
        )
        await self._session.flush()

        details: list[dict[str, Any]] = [
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
        await self._insert_in_batches(ClosingDetail, details)

        # Uma linha por movimento do Banka (~18k, a par dos detalhes): é o que
        # permite abrir um fecho e ver as parcelas do crédito da chave.
        movements: list[dict[str, Any]] = [
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
        await self._insert_in_batches(CreditMovement, movements)

        cases: list[dict[str, Any]] = [
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
            await self._session.execute(sa.insert(PendingCase), cases)

        return execution_id

    async def _insert_in_batches(self, table: type[Any], rows: list[dict[str, Any]]) -> None:
        for start in range(0, len(rows), INSERT_BATCH):
            batch = rows[start : start + INSERT_BATCH]
            if batch:
                await self._session.execute(sa.insert(table), batch)

    async def find(self, execution_id: str) -> Execution | None:
        return await self._session.get(Execution, execution_id)

    async def find_latest(self) -> Execution | None:
        result = await self._session.execute(
            sa.select(Execution).order_by(Execution.executedAt.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def list_details(
        self,
        execution_id: str,
        page: Page,
        validation: str | None = None,
        search: str | None = None,
    ) -> tuple[list[ClosingDetail], int]:
        where = _details_where(execution_id, validation, search)
        items_result = await self._session.execute(
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
        total_result = await self._session.execute(
            sa.select(sa.func.count()).select_from(ClosingDetail).where(*where)
        )
        return list(items_result.scalars().all()), total_result.scalar_one()

    async def list_all_details(self, execution_id: str) -> list[ClosingDetail]:
        """Todos os detalhes da execução, na ordem natural do relatório."""
        result = await self._session.execute(
            sa.select(ClosingDetail)
            .where(ClosingDetail.executionId == execution_id)
            .order_by(ClosingDetail.posId.asc(), ClosingDetail.period.asc())
        )
        return list(result.scalars().all())

    async def list_details_by_key(self, execution_id: str, key: str) -> list[ClosingDetail]:
        """Os fechos SIMO de uma chave, na ordem em que o operador os lê."""
        result = await self._session.execute(
            sa.select(ClosingDetail)
            .where(ClosingDetail.executionId == execution_id, ClosingDetail.key == key)
            .order_by(ClosingDetail.simoClosingDate.asc(), ClosingDetail.operationNumber.asc())
        )
        return list(result.scalars().all())

    async def list_movements_by_key(self, execution_id: str, key: str) -> list[CreditMovement]:
        """Os movimentos de crédito do Banka de uma chave, por data."""
        result = await self._session.execute(
            sa.select(CreditMovement)
            .where(CreditMovement.executionId == execution_id, CreditMovement.key == key)
            .order_by(CreditMovement.movementDate.asc())
        )
        return list(result.scalars().all())

    async def count_details_by_validation(
        self, execution_id: str, search: str | None = None
    ) -> dict[str, int]:
        """Contagens para os chips — sobre TODAS as linhas da execução, não da página."""
        counts: dict[str, int] = {"all": 0, **dict.fromkeys(Validation, 0)}
        where = _details_where(execution_id, None, search)
        result = await self._session.execute(
            sa.select(ClosingDetail.validation, sa.func.count())
            .where(*where)
            .group_by(ClosingDetail.validation)
        )
        for validation, total in result.all():
            counts[validation] = total
            counts["all"] += total
        return counts

    async def save_summary(self, execution_id: str, summary: dict[str, Any]) -> None:
        await self._session.execute(
            sa.update(Execution).where(Execution.id == execution_id).values(summary=summary)
        )


def _details_where(execution_id: str, validation: str | None, search: str | None) -> list[Any]:
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
