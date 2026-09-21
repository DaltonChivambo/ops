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

# O Postgres aceita inserções grandes, mas lotes desta ordem mantêm a memória
# estável nas ~18k linhas de uma execução real.
INSERT_BATCH = 5_000

VALIDATION_STATES = frozenset(Validation)

# Ordem de leitura do operador na tabela de fechos — a mesma dos casos (ver
# `CaseRepository._TYPE_ORDER`) e a do relatório: incorrecto e não creditado à
# frente, que é onde há dinheiro errado ou dinheiro em falta; períodos repetidos
# a seguir (ambiguidade a desfazer, não divergência); depois os fechos com linha
# repetida na SIMO, juntos num bloco (não são anomalia, mas vêem-se); confere
# depois; zerado por último, que não pede nada a ninguém. Não é a ordem de
# declaração do enum `Validation` (essa é `zero, match, mismatch, missing,
# duplicated`, contrato da migração `9e88fa0665cd`) — só a leitura muda.
_VALIDATION_ORDER = sa.case(
    (ClosingDetail.validation == Validation.MISMATCH, 0),
    (ClosingDetail.validation == Validation.MISSING, 1),
    (ClosingDetail.validation == Validation.DUPLICATED, 2),
    (sa.or_(ClosingDetail.simo_duplicate, ClosingDetail.has_simo_duplicate), 3),
    (ClosingDetail.validation == Validation.MATCH, 4),
    (ClosingDetail.validation == Validation.ZERO, 5),
)

# As cópias do export da SIMO não são fechos da chave: ficam fora do que se
# concilia e do que se conta por chave.
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
                "simo_duplicate": detail.simo_duplicate,
                "has_simo_duplicate": detail.has_simo_duplicate,
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
        repeated: RepeatedClosings = RepeatedClosings.ALL,
    ) -> tuple[list[ClosingDetail], int]:
        where = _details_where(execution_id, validation, search, repeated)
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
                # A original antes das suas linhas duplicadas na SIMO: o ecrã junta-as.
                ClosingDetail.simo_duplicate.asc(),
                ClosingDetail.operation_number.asc(),
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
        # Sem o `repeated`: as contagens são as da execução inteira, e é o que
        # faz as três hipóteses do filtro somarem «todos» em vez de se contarem
        # a si próprias.
        where = _details_where(execution_id, None, search)
        # Os fechos repetidos na SIMO entram em «todos», mas não no estado do
        # original: não são mais um fecho a conferir nem a tratar.
        result = await self._session.execute(
            sa.select(ClosingDetail.validation, ClosingDetail.simo_duplicate, sa.func.count())
            .where(*where)
            .group_by(ClosingDetail.validation, ClosingDetail.simo_duplicate)
        )
        for validation, simo_duplicate, total in result.all():
            if simo_duplicate:
                # O número de «Apenas os repetidos»: só as cópias, o mesmo que
                # o resumo e o relatório — e o mesmo que o filtro traz. O
                # original de cada uma vê-se ao abrir o fecho.
                counts["simo_duplicates"] += total
            else:
                counts[validation] += total
            counts["all"] += total
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
            .values(validation=validation, difference=difference)
        )

    async def duplicated_totals(self, execution_id: str) -> tuple[int, Decimal, Decimal] | None:
        """O que ainda está em «períodos repetidos»: nº de fechos, soma SIMO e soma Banka.

        O Banka conta só os movimentos das chaves com fechos por conciliar que
        nenhum par levou — os que já têm par estão em «confere», e os que sobram
        numa chave toda conciliada não são fecho nenhum da SIMO. `None` numa
        execução sem movimentos guardados (anterior à migração que os passou a
        gravar): aí não há como recontar o Banka.

        Em dois passos, com a lista de chaves na mão — ver a nota de desempenho
        em `list_details`: subconsultas sobre as duas tabelas grandes de uma
        execução acabada de gravar deixavam o Postgres minutos preso.
        """
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
        # Chave a chave e não uma soma só: o lado do Banka nunca passa o da SIMO
        # — a mesma regra do `compute_summary`, e pela mesma razão (crédito de um
        # período que colide em `% 1000` não é crédito desta chave).
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
        """Grava a decisão sobre os fechos repetidos da SIMO e refaz o apuramento.

        **Nada se revalida.** O estado de cada fecho é o que está gravado, e isso
        inclui os que uma conciliação já pôs em «confere». O que muda é só se os
        fechos repetidos contam, e é a `with_simo_duplicates` que diz onde eles
        entram: no estado da chave deles, nunca num estado próprio.
        """
        updated = with_simo_duplicates(summary, await self._repeated_keys(execution_id), counted)
        await self._session.execute(
            sa.update(Execution)
            .where(Execution.id == execution_id)
            .values(summary=updated, count_simo_duplicates=counted)
        )
        return updated

    async def _repeated_keys(self, execution_id: str) -> list[KeyTally]:
        """As chaves COM fechos repetidos, com o que eles valem e o que a chave já pesa.

        Só essas: o apuramento das outras não muda com esta decisão, e mexer-lhes
        desfazia o que as conciliações já acertaram no `summary`.

        `simoKeyTotal` e `bankaClosingTotal` são da chave e repetem-se em todas
        as linhas dela — daí `MAX` e não `SUM`. A validação sai dos próprios
        fechos repetidos: é nesse estado que eles vão contar.
        """
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
    # «Só os repetidos» são as cópias, e não o par: é assim que os três números
    # do filtro somam o total, e o original de cada uma vê-se ao abrir o fecho.
    if repeated is RepeatedClosings.ONLY:
        conditions.append(ClosingDetail.simo_duplicate)
    elif repeated is RepeatedClosings.WITHOUT:
        conditions.append(ClosingDetail.simo_duplicate.is_(False))
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
