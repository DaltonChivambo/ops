"""Acesso a dados da execução e de tudo o que lhe pertence.

Porte de `repositories.py` do MozaOps v1 (Prisma → SQLAlchemy async). Esta
camada e a `CaseRepository` são as ÚNICAS que importam `sqlalchemy`: é isso que
mantém a troca de ORM contida aqui.

**A sessão vem de fora, e nunca se cria aqui.** É a regra que substitui uma
unit of work: quem abre a sessão é o `Depends` do pedido, o repositório apenas a
recebe, e é por isso que tudo o que corre num pedido partilha a transacção.
"""

import uuid
from collections.abc import Collection, Mapping
from decimal import Decimal
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import ReconciliationResult
from app.domain.vocabulary import CaseStatus, CaseType, UploadSlot, Validation
from app.infrastructure.tables import (
    ClosingDetail,
    ClosingMatch,
    CreditMovement,
    Execution,
    PendingCase,
)
from app.pagination import Page

# O Postgres aceita inserções grandes, mas lotes desta ordem mantêm a memória
# estável nas ~18k linhas de uma execução real.
INSERT_BATCH = 5_000

VALIDATION_STATES = frozenset(Validation)

# Ordem de leitura do operador na tabela de fechos — a mesma dos casos (ver
# `CaseRepository._TYPE_ORDER`): incorrecto, duplicado, não creditado à
# frente, por exigirem trabalho; confere depois; zerado por último, que não
# pede nada a ninguém. Não é a ordem de declaração do enum `Validation`
# (essa é `zero, match, mismatch, missing, duplicated`, contrato da migração
# `9e88fa0665cd`) — só a leitura muda, não a base.
_VALIDATION_ORDER = sa.case(
    (ClosingDetail.validation == Validation.MISMATCH, 0),
    (ClosingDetail.validation == Validation.DUPLICATED, 1),
    (ClosingDetail.validation == Validation.MISSING, 2),
    (ClosingDetail.validation == Validation.MATCH, 3),
    (ClosingDetail.validation == Validation.ZERO, 4),
)


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
                period_start=result.period_start,
                period_end=result.period_end,
                report_name=result.report_name,
                pos_list_file=files[UploadSlot.POS_LIST],
                simo_closings_file=files[UploadSlot.SIMO_CLOSINGS],
                banka_credits_file=files[UploadSlot.BANKA_CREDITS],
                summary=summary,
            )
        )
        await self._session.flush()

        # As chaves são os NOMES DOS ATRIBUTOS da ORM (o SQLAlchemy mapeia-os
        # para as colunas), não os nomes das colunas.
        details: list[dict[str, Any]] = [
            {
                "id": str(uuid.uuid4()),
                "execution_id": execution_id,
                "pos_id": detail.pos_id,
                "merchant": detail.merchant,
                "account_number": detail.account_number,
                "period": detail.period,
                "key": detail.key,
                "simo_closing_date": detail.simo_closing_date,
                "operation_number": detail.operation_number,
                "simo_closing_total": detail.simo_closing_total,
                "simo_key_total": detail.simo_key_total,
                "closing_description": detail.closing_description,
                "banka_credit_date": detail.banka_credit_date,
                "banka_closing_total": detail.banka_closing_total,
                "closing_type": detail.closing_type,
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
                "execution_id": execution_id,
                "key": movement.key,
                "movement_date": movement.date,
                "amount": movement.amount,
                "description": movement.description,
            }
            for movement in result.movements
        ]
        await self._insert_in_batches(CreditMovement, movements)

        cases: list[dict[str, Any]] = [
            {
                "id": str(uuid.uuid4()),
                "execution_id": execution_id,
                "key": case.key,
                "pos_id": case.pos_id,
                "period": case.period,
                "merchant": case.merchant,
                "account_number": case.account_number,
                "simo_amount": case.simo_amount,
                "banka_amount": case.banka_amount,
                "type": case.type,
                "first_date": case.first_date,
                "first_date_source": case.first_date_source,
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
            sa.select(Execution).order_by(Execution.executed_at.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def list_details(
        self,
        execution_id: str,
        page: Page,
        validation: str | None = None,
        search: str | None = None,
        unmatched_credits_only: bool = False,
    ) -> tuple[list[ClosingDetail], int]:
        where = _details_where(execution_id, validation, search, unmatched_credits_only)
        items_result = await self._session.execute(
            sa.select(ClosingDetail)
            .where(*where)
            # Ver `_VALIDATION_ORDER`. Dentro do tipo ordena-se por chave e depois
            # por data, para as linhas da mesma chave ficarem contíguas e a tabela
            # as poder agrupar.
            .order_by(
                _VALIDATION_ORDER,
                ClosingDetail.pos_id.asc(),
                ClosingDetail.period.asc(),
                ClosingDetail.simo_closing_date.asc(),
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
            .where(ClosingDetail.execution_id == execution_id)
            .order_by(ClosingDetail.pos_id.asc(), ClosingDetail.period.asc())
        )
        return list(result.scalars().all())

    async def list_details_by_key(self, execution_id: str, key: str) -> list[ClosingDetail]:
        """Os fechos SIMO de uma chave, na ordem em que o operador os lê."""
        return await self.list_details_by_keys(execution_id, [key])

    async def list_details_by_keys(
        self, execution_id: str, keys: Collection[str]
    ) -> list[ClosingDetail]:
        """Os fechos SIMO de várias chaves numa query só — juntos por chave, e por data."""
        if not keys:
            return []
        result = await self._session.execute(
            sa.select(ClosingDetail)
            .where(ClosingDetail.execution_id == execution_id, ClosingDetail.key.in_(keys))
            .order_by(
                ClosingDetail.key.asc(),
                ClosingDetail.simo_closing_date.asc(),
                ClosingDetail.operation_number.asc(),
            )
        )
        return list(result.scalars().all())

    async def list_movements_by_key(self, execution_id: str, key: str) -> list[CreditMovement]:
        """Os movimentos de crédito do Banka de uma chave, por data."""
        return await self.list_movements_by_keys(execution_id, [key])

    async def list_movements_by_keys(
        self, execution_id: str, keys: Collection[str]
    ) -> list[CreditMovement]:
        """Os movimentos do Banka de várias chaves numa query só — juntos por chave, e por data."""
        if not keys:
            return []
        result = await self._session.execute(
            sa.select(CreditMovement)
            .where(CreditMovement.execution_id == execution_id, CreditMovement.key.in_(keys))
            .order_by(CreditMovement.key.asc(), CreditMovement.movement_date.asc())
        )
        return list(result.scalars().all())

    async def count_details_by_validation(
        self, execution_id: str, search: str | None = None
    ) -> dict[str, int]:
        """Contagens para os chips — sobre TODAS as linhas da execução, não da página."""
        counts: dict[str, int] = {"all": 0, "unmatched": 0, **dict.fromkeys(Validation, 0)}
        where = _details_where(execution_id, None, search)
        result = await self._session.execute(
            sa.select(ClosingDetail.validation, sa.func.count())
            .where(*where)
            .group_by(ClosingDetail.validation)
        )
        for validation, total in result.all():
            counts[validation] = total
            counts["all"] += total
        # Os fechos das chaves com crédito sem fecho — o número do filtro, que não é
        # um estado: estes fechos já estão em «confere».
        unmatched = await self._session.execute(
            sa.select(sa.func.count())
            .select_from(ClosingDetail)
            .where(*_details_where(execution_id, None, search, unmatched_credits_only=True))
        )
        counts["unmatched"] = unmatched.scalar_one()
        return counts

    async def count_by_key(
        self, execution_id: str, keys: Collection[str]
    ) -> dict[str, tuple[int, int]]:
        """(nº fechos SIMO, nº movimentos Banka) por chave — só para as chaves pedidas.

        Chamado só com as chaves `duplicated` de uma página/lista, nunca com a
        execução inteira: é o que desfaz, no frontend, a ambiguidade entre uma
        chave com vários fechos na SIMO e uma com um só fecho mas vários
        movimentos no Banka (ver a nota central em `domain/reconciliation.py`).
        Duas queries planas em vez de um join — as duas tabelas não têm FK
        entre si, e um join duplicaria linhas ou pedia `COUNT(DISTINCT ...)`.
        """
        if not keys:
            return {}
        simo = await self._session.execute(
            sa.select(ClosingDetail.key, sa.func.count())
            .where(ClosingDetail.execution_id == execution_id, ClosingDetail.key.in_(keys))
            .group_by(ClosingDetail.key)
        )
        simo_counts: dict[str, int] = {}
        for key, count in simo.all():
            simo_counts[key] = count
        banka = await self._session.execute(
            sa.select(CreditMovement.key, sa.func.count())
            .where(CreditMovement.execution_id == execution_id, CreditMovement.key.in_(keys))
            .group_by(CreditMovement.key)
        )
        banka_counts: dict[str, int] = {}
        for key, count in banka.all():
            banka_counts[key] = count
        return {key: (simo_counts.get(key, 0), banka_counts.get(key, 0)) for key in keys}

    async def set_closings_validation(
        self,
        execution_id: str,
        closing_ids: Collection[str],
        validation: Validation,
        difference: Decimal | None,
    ) -> None:
        """Muda o estado de fechos já gravados — é o que a conciliação faz a um fecho."""
        if not closing_ids:
            return
        await self._session.execute(
            sa.update(ClosingDetail)
            .where(ClosingDetail.execution_id == execution_id, ClosingDetail.id.in_(closing_ids))
            .values(validation=validation, difference=difference)
        )

    async def sum_unmatched_credits(self, execution_id: str) -> tuple[int, Decimal]:
        """Créditos do Banka sem fecho, por analisar — quantos, e quanto somam.

        Contam os créditos que nenhum par levou, nas chaves de períodos duplicados
        em que todos os fechos já estão conciliados e o caso continua aberto. É
        dinheiro que ficou por explicar depois de a conciliação arrumar os fechos
        — ver `settles_case`. Numa chave ainda com fechos por ligar, os créditos
        soltos continuam a contar como período duplicado; quando o caso fecha,
        saem daqui.
        """
        result = await self._session.execute(
            sa.select(
                sa.func.count(), sa.func.coalesce(sa.func.sum(CreditMovement.amount), 0)
            ).where(*_unmatched_credits_where(execution_id))
        )
        count, total = result.one()
        return int(count), Decimal(total)

    async def unmatched_credits_by_key(
        self, execution_id: str, keys: Collection[str]
    ) -> dict[str, tuple[int, Decimal]]:
        """Os mesmos créditos sem fecho, por chave — só para as chaves pedidas (uma página)."""
        if not keys:
            return {}
        result = await self._session.execute(
            sa.select(CreditMovement.key, sa.func.count(), sa.func.sum(CreditMovement.amount))
            .where(*_unmatched_credits_where(execution_id), CreditMovement.key.in_(keys))
            .group_by(CreditMovement.key)
        )
        return {key: (int(count), Decimal(total)) for key, count, total in result.all()}

    async def save_summary(self, execution_id: str, summary: dict[str, Any]) -> None:
        await self._session.execute(
            sa.update(Execution).where(Execution.id == execution_id).values(summary=summary)
        )


def _unmatched_credits_where(execution_id: str) -> list[Any]:
    """O que é um crédito sem fecho por analisar — a definição única, em condições sobre
    `CreditMovement`, usada no total do `summary`, no filtro da tabela e em cada linha.

    Um crédito que nenhum par levou, numa chave de períodos duplicados em que todos
    os fechos já estão conciliados e o caso continua aberto. Numa chave ainda com
    fechos por ligar, os créditos soltos contam como período duplicado; quando o
    caso fecha, saem daqui. Ver `settles_case`.

    Só os do intervalo da execução: um crédito com data depois do último dia é do
    intervalo seguinte, e não conta (ver `within_period`).
    """
    open_keys = sa.select(PendingCase.key).where(
        PendingCase.execution_id == execution_id,
        PendingCase.type == CaseType.DUPLICATED,
        PendingCase.status != CaseStatus.RESOLVED,
    )
    reconciled_keys = sa.select(ClosingMatch.key).where(ClosingMatch.execution_id == execution_id)
    keys_with_unmatched_closings = sa.select(ClosingDetail.key).where(
        ClosingDetail.execution_id == execution_id,
        ClosingDetail.validation == Validation.DUPLICATED,
    )
    used_movements = sa.select(ClosingMatch.movement_id).where(
        ClosingMatch.execution_id == execution_id
    )
    period_end = (
        sa.select(Execution.period_end).where(Execution.id == execution_id).scalar_subquery()
    )
    return [
        CreditMovement.execution_id == execution_id,
        CreditMovement.key.in_(open_keys),
        CreditMovement.key.in_(reconciled_keys),
        CreditMovement.key.not_in(keys_with_unmatched_closings),
        CreditMovement.id.not_in(used_movements),
        sa.or_(
            CreditMovement.movement_date.is_(None),
            CreditMovement.movement_date <= period_end,
        ),
    ]


def _details_where(
    execution_id: str,
    validation: str | None,
    search: str | None,
    unmatched_credits_only: bool = False,
) -> list[Any]:
    conditions: list[Any] = [ClosingDetail.execution_id == execution_id]
    if unmatched_credits_only:
        # Os fechos das chaves que têm créditos do Banka sem fecho por analisar.
        conditions.append(
            ClosingDetail.key.in_(
                sa.select(CreditMovement.key).where(*_unmatched_credits_where(execution_id))
            )
        )
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
                    ClosingDetail.pos_id.ilike(pattern),
                    ClosingDetail.merchant.ilike(pattern),
                    ClosingDetail.account_number.ilike(pattern),
                )
            )
    return conditions
