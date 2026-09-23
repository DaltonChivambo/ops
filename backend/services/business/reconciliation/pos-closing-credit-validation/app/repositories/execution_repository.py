"""Acesso a dados da execução e de tudo o que lhe pertence."""

import uuid
from collections.abc import Collection, Mapping
from decimal import Decimal
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import ReconciliationResult
from app.domain.reconciliation import KeyTally, with_simo_duplicates
from app.domain.vocabulary import RepeatedClosings, UploadSlot, Validation
from app.infrastructure.tables import (
    ClosingDetail,
    ClosingMatch,
    CreditMovement,
    Execution,
    PendingCase,
)
from app.pagination import Page

# Lotes desta ordem mantêm a memória estável nas ~18k linhas de uma execução.
INSERT_BATCH = 5_000

VALIDATION_STATES = frozenset(Validation)

# Ordem de leitura do operador, a mesma dos casos e do relatório: incorrecto,
# não creditado, períodos repetidos, linha repetida na SIMO, confere, zerado.
# Não é a ordem de declaração do enum `Validation`.
# Vive numa coluna (`sortRank`) porque uma expressão no `ORDER BY` não é indexável.
_RANK_BY_VALIDATION = {
    Validation.MISMATCH: 0,
    Validation.MISSING: 1,
    Validation.DUPLICATED: 2,
    Validation.MATCH: 4,
    Validation.ZERO: 5,
}
_REPEATED_RANK = 3


def sort_rank(validation: Validation, simo_duplicate: bool, has_simo_duplicate: bool) -> int:
    rank = _RANK_BY_VALIDATION[validation]
    if rank > _REPEATED_RANK and (simo_duplicate or has_simo_duplicate):
        return _REPEATED_RANK
    return rank


def _sort_rank_value(validation: Validation) -> sa.ColumnElement[int] | int:
    """O mesmo cálculo em SQL, para quando o estado muda e as marcas ficam."""
    rank = _RANK_BY_VALIDATION[validation]
    if rank < _REPEATED_RANK:
        return rank
    return sa.case(
        (sa.or_(ClosingDetail.simo_duplicate, ClosingDetail.has_simo_duplicate), _REPEATED_RANK),
        else_=rank,
    )


# As cópias do export ficam fora do que se concilia e do que se conta por chave.
_REAL_CLOSING = ClosingDetail.simo_duplicate.is_(False)


class ExecutionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        result: ReconciliationResult,
        files: Mapping[UploadSlot, str],
        summary: dict[str, Any],
    ) -> str:
        """Persiste execução + detalhes + movimentos + casos numa única transacção."""
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

        # As chaves são nomes de atributos da ORM, não nomes de colunas.
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
                "simo_duplicate": detail.simo_duplicate,
                "has_simo_duplicate": detail.has_simo_duplicate,
                "sort_rank": sort_rank(
                    detail.validation, detail.simo_duplicate, detail.has_simo_duplicate
                ),
            }
            for detail in result.details
        ]
        await self._insert_in_batches(ClosingDetail, details)

        # Uma linha por movimento do Banka (~18k), para se abrirem as parcelas da chave.
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
        repeated: RepeatedClosings = RepeatedClosings.ALL,
    ) -> list[ClosingDetail]:
        where = _details_where(execution_id, validation, search, repeated)
        items_result = await self._session.execute(
            sa.select(ClosingDetail)
            .where(*where)
            # Esta lista é a do `ix_closing_detail_reading_order`. Dentro do tipo,
            # por chave e data, para as linhas da mesma chave ficarem contíguas.
            .order_by(
                ClosingDetail.sort_rank.asc(),
                ClosingDetail.pos_id.asc(),
                ClosingDetail.period.asc(),
                ClosingDetail.simo_closing_date.asc(),
                # A original antes das suas cópias: o ecrã junta-as.
                ClosingDetail.simo_duplicate.asc(),
                ClosingDetail.operation_number.asc(),
            )
            .offset(page.skip)
            .limit(page.take)
        )
        return list(items_result.scalars().all())

    async def count_details(
        self,
        execution_id: str,
        validation: str | None = None,
        search: str | None = None,
        repeated: RepeatedClosings = RepeatedClosings.ALL,
    ) -> int:
        """Quantas linhas tem a consulta inteira. Separado da página de propósito:"""
        where = _details_where(execution_id, validation, search, repeated)
        result = await self._session.execute(
            sa.select(sa.func.count()).select_from(ClosingDetail).where(*where)
        )
        return result.scalar_one()

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
            .where(
                ClosingDetail.execution_id == execution_id,
                ClosingDetail.key.in_(keys),
                _REAL_CLOSING,
            )
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
        counts: dict[str, int] = {"all": 0, "simo_duplicates": 0, **dict.fromkeys(Validation, 0)}
        # Sem o `repeated`: as contagens são da execução inteira, e é o que faz
        # as três hipóteses do filtro somarem «todos».
        where = _details_where(execution_id, None, search)
        # Os repetidos entram em «todos», mas não no estado do original.
        result = await self._session.execute(
            sa.select(ClosingDetail.validation, ClosingDetail.simo_duplicate, sa.func.count())
            .where(*where)
            .group_by(ClosingDetail.validation, ClosingDetail.simo_duplicate)
        )
        for validation, simo_duplicate, total in result.all():
            if simo_duplicate:
                # «Só os repetidos» são as cópias, o mesmo que o resumo e o relatório.
                counts["simo_duplicates"] += total
            else:
                counts[validation] += total
            counts["all"] += total
        return counts

    async def count_by_key(
        self, execution_id: str, keys: Collection[str]
    ) -> dict[str, tuple[int, int]]:
        """(nº fechos SIMO, nº movimentos Banka) por chave — só para as chaves pedidas."""
        if not keys:
            return {}
        simo = await self._session.execute(
            sa.select(ClosingDetail.key, sa.func.count())
            .where(
                ClosingDetail.execution_id == execution_id,
                ClosingDetail.key.in_(keys),
                _REAL_CLOSING,
            )
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
            .values(
                validation=validation,
                difference=difference,
                sort_rank=_sort_rank_value(validation),
            )
        )

    async def duplicated_totals(self, execution_id: str) -> tuple[int, Decimal, Decimal] | None:
        """O que ainda está em «períodos repetidos»: nº de fechos, soma SIMO e soma Banka."""
        has_movements = await self._session.execute(
            sa.select(CreditMovement.id).where(CreditMovement.execution_id == execution_id).limit(1)
        )
        if has_movements.first() is None:
            return None

        closings = await self._session.execute(
            sa.select(
                ClosingDetail.key,
                sa.func.count(),
                sa.func.coalesce(sa.func.sum(ClosingDetail.simo_closing_total), 0),
            )
            .where(
                ClosingDetail.execution_id == execution_id,
                ClosingDetail.validation == Validation.DUPLICATED,
                _REAL_CLOSING,
            )
            .group_by(ClosingDetail.key)
        )
        count, simo = 0, Decimal(0)
        simo_by_key: dict[str, Decimal] = {}
        for key, key_count, key_simo in closings.all():
            simo_by_key[key] = Decimal(key_simo)
            count += key_count
            simo += Decimal(key_simo)
        if not simo_by_key:
            return 0, Decimal(0), Decimal(0)

        keys = list(simo_by_key)
        used = await self._session.execute(
            sa.select(ClosingMatch.movement_id).where(
                ClosingMatch.execution_id == execution_id, ClosingMatch.key.in_(keys)
            )
        )
        used_ids = list(used.scalars().all())
        banka_where = [CreditMovement.execution_id == execution_id, CreditMovement.key.in_(keys)]
        if used_ids:
            banka_where.append(CreditMovement.id.not_in(used_ids))
        # Chave a chave: o Banka nunca passa a SIMO — a regra do `compute_summary`.
        banka_rows = await self._session.execute(
            sa.select(CreditMovement.key, sa.func.coalesce(sa.func.sum(CreditMovement.amount), 0))
            .where(*banka_where)
            .group_by(CreditMovement.key)
        )
        banka = sum(
            (min(Decimal(amount), simo_by_key.get(key, Decimal(0))) for key, amount in banka_rows),
            Decimal(0),
        )
        return count, simo, banka

    async def set_count_simo_duplicates(
        self, execution_id: str, counted: bool, summary: dict[str, Any]
    ) -> dict[str, Any]:
        """Grava a decisão sobre os fechos repetidos da SIMO e refaz o apuramento."""
        updated = with_simo_duplicates(summary, await self._repeated_keys(execution_id), counted)
        await self._session.execute(
            sa.update(Execution)
            .where(Execution.id == execution_id)
            .values(summary=updated, count_simo_duplicates=counted)
        )
        return updated

    async def _repeated_keys(self, execution_id: str) -> list[KeyTally]:
        """As chaves COM fechos repetidos, com o que eles valem e o que a chave já pesa."""
        rows = await self._session.execute(
            sa.select(
                ClosingDetail.validation,
                sa.func.max(ClosingDetail.simo_key_total),
                sa.func.max(sa.func.coalesce(ClosingDetail.banka_closing_total, 0)),
                sa.func.count(),
                sa.func.sum(ClosingDetail.simo_closing_total),
            )
            .where(ClosingDetail.execution_id == execution_id, ClosingDetail.simo_duplicate)
            .group_by(ClosingDetail.key, ClosingDetail.validation)
        )
        return [
            KeyTally(
                validation=validation,
                simo=Decimal(simo),
                banka=Decimal(banka),
                repeated=repeated,
                repeated_amount=Decimal(amount),
            )
            for validation, simo, banka, repeated, amount in rows.all()
        ]

    async def save_summary(self, execution_id: str, summary: dict[str, Any]) -> None:
        await self._session.execute(
            sa.update(Execution).where(Execution.id == execution_id).values(summary=summary)
        )


def _details_where(
    execution_id: str,
    validation: str | None,
    search: str | None,
    repeated: RepeatedClosings = RepeatedClosings.ALL,
) -> list[Any]:
    conditions: list[Any] = [ClosingDetail.execution_id == execution_id]
    # «Só os repetidos» são as cópias e não o par: é assim que os três somam o total.
    if repeated is RepeatedClosings.ONLY:
        conditions.append(ClosingDetail.simo_duplicate)
    elif repeated is RepeatedClosings.WITHOUT:
        conditions.append(ClosingDetail.simo_duplicate.is_(False))
    if validation:
        # Estados a mostrar, separados por vírgulas. Tokens desconhecidos caem fora,
        # e uma selecção vazia não devolve nada; parâmetro ausente ou vazio não filtra.
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
