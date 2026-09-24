"""Caso de uso da validação: executar, consultar e gerar o relatório."""

import asyncio
import logging
import time
from collections import defaultdict
from collections.abc import Iterable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from typing import IO, Any, Protocol

from app.domain.errors import NotFoundError
from app.domain.matching import Match, is_fully_matched, suggest_matches
from app.domain.models import ReconciliationResult
from app.domain.reconciliation import reconcile
from app.domain.vocabulary import CaseType, RepeatedClosings, UploadSlot, Validation
from app.infrastructure.excel import parsers, report
from app.infrastructure.tables import (
    ClosingDetail,
    ClosingMatch,
    CreditMovement,
    Execution,
    PendingCase,
)
from app.pagination import Page
from app.repositories.case_repository import CaseRepository
from app.repositories.execution_repository import ExecutionRepository
from app.repositories.match_repository import MatchRepository
from app.services.match_sides import closing_side, movement_side

logger = logging.getLogger("pos_closing_credit_validation")


@dataclass(frozen=True, slots=True)
class DetailsPage:
    """Uma página da tabela de fechos, com o que cada linha precisa além do fecho."""

    details: list[ClosingDetail]
    # `None` a partir da segunda página: são as duas leituras que varrem tudo.
    total: int | None
    # Contagens dos filtros, sobre a execução inteira.
    counts: dict[str, int] | None
    # (nº de fechos SIMO, nº de movimentos Banka) das chaves duplicadas.
    key_counts: dict[str, tuple[int, int]]


@dataclass(frozen=True, slots=True)
class ReconciliationCandidate:
    """Um caso de períodos repetidos com tudo o que é preciso para o conciliar."""

    case: PendingCase
    closings: list[ClosingDetail]
    movements: list[CreditMovement]
    matches: list[ClosingMatch]
    suggested_matches: list[Match]


class ValidationService:
    def __init__(
        self,
        executions: ExecutionRepository,
        cases: CaseRepository,
        matches: MatchRepository,
    ) -> None:
        self._executions = executions
        self._cases = cases
        self._matches = matches

    async def run(self, files: Mapping[UploadSlot, tuple[IO[bytes], str]]) -> str:
        """Executa a validação e devolve o id da execução persistida."""
        result = await asyncio.to_thread(_parse_and_reconcile, files)
        names = {slot: files[slot][1] for slot in UploadSlot}
        with _timed("gravação"):
            return await self._executions.create(result, names, result.summary.to_json_dict())

    async def get_execution(self, execution_id: str) -> Execution:
        execution = await self._executions.find(execution_id)
        if execution is None:
            raise NotFoundError("A execução indicada não existe ou já foi removida.")
        return execution

    async def get_latest_execution(self) -> Execution | None:
        return await self._executions.find_latest()

    async def set_count_simo_duplicates(self, execution_id: str, counted: bool) -> dict[str, Any]:
        """Manda contar, ou não, os fechos repetidos do export da SIMO nos montantes."""
        execution = await self.get_execution(execution_id)
        summary = dict(execution.summary or {})
        if execution.count_simo_duplicates == counted:
            return summary
        return await self._executions.set_count_simo_duplicates(execution_id, counted, summary)

    async def list_cases(
        self, execution_id: str
    ) -> tuple[list[PendingCase], dict[str, tuple[int, int]]]:
        cases = await self._cases.list_by_execution(execution_id)
        duplicated_keys = {case.key for case in cases if case.type == CaseType.DUPLICATED}
        key_counts = await self._executions.count_by_key(execution_id, duplicated_keys)
        return cases, key_counts

    async def list_details(
        self,
        execution_id: str,
        page: Page,
        validation: str | None,
        search: str | None,
        repeated: RepeatedClosings = RepeatedClosings.ALL,
    ) -> DetailsPage:
        details = await self._executions.list_details(
            execution_id, page, validation, search, repeated
        )
        first_page = page.page == 1
        duplicated_keys = {
            detail.key for detail in details if detail.validation == Validation.DUPLICATED
        }
        return DetailsPage(
            details=details,
            total=(
                await self._executions.count_details(execution_id, validation, search, repeated)
                if first_page
                else None
            ),
            counts=(
                await self._executions.count_details_by_validation(execution_id, search)
                if first_page
                else None
            ),
            key_counts=await self._executions.count_by_key(execution_id, duplicated_keys),
        )

    async def get_key_breakdown(self, execution_id: str, key: str) -> dict[str, Any]:
        """Os dois lados de uma chave: os fechos da SIMO e os movimentos do Banka."""
        await self.get_execution(execution_id)  # 404 se a execução não existir
        details = await self._executions.list_details_by_key(execution_id, key)
        if not details:
            raise NotFoundError("Não há nenhum fecho com esta chave nesta execução.")
        movements = await self._executions.list_movements_by_key(execution_id, key)
        return {
            "key": key,
            "closings": details,
            "movements": movements,
            "case": await self._cases.find_by_key(execution_id, key),
            # O que já foi conciliado e o que se pode conciliar só pelo valor.
            # A sugestão vai sempre; a regra do par vive em `domain/matching.py`.
            "matches": await self._matches.list_by_key(execution_id, key),
            "suggested_matches": suggest_matches(
                [closing_side(row) for row in details],
                [movement_side(row) for row in movements],
            ),
        }

    async def list_reconciliation_candidates(
        self, execution_id: str
    ) -> list[ReconciliationCandidate]:
        """As chaves que se conciliam com crédito igual, fecho a fecho."""
        await self.get_execution(execution_id)  # 404 se a execução não existir
        cases = await self._cases.list_open_duplicated(execution_id)
        keys = [case.key for case in cases]
        closings = _group_by_key(await self._executions.list_details_by_keys(execution_id, keys))
        movements = _group_by_key(await self._executions.list_movements_by_keys(execution_id, keys))
        matches = _group_by_key(await self._matches.list_by_keys(execution_id, keys))

        candidates: list[ReconciliationCandidate] = []
        for case in cases:
            if matches.get(case.key):
                continue
            key_closings = closings.get(case.key, [])
            key_movements = movements.get(case.key, [])
            closing_sides = [closing_side(row) for row in key_closings]
            suggested = suggest_matches(
                closing_sides, [movement_side(row) for row in key_movements]
            )
            if not is_fully_matched(suggested, closing_sides):
                continue
            candidates.append(
                ReconciliationCandidate(
                    case=case,
                    closings=key_closings,
                    movements=key_movements,
                    matches=[],
                    suggested_matches=suggested,
                )
            )
        return candidates

    async def build_report(self, execution_id: str) -> tuple[bytes, str]:
        """Gera o .xlsx da execução a partir do que está persistido."""
        execution = await self.get_execution(execution_id)
        details = await self._executions.list_all_details(execution_id)
        cases = await self._cases.list_by_execution(execution_id)
        content = await asyncio.to_thread(report.build_workbook, execution, details, cases)
        return content, f"{execution.report_name}.xlsx"


class _Keyed(Protocol):
    # Propriedade e não atributo: nas tabelas `key` é um `Mapped[str]`.
    @property
    def key(self) -> str: ...


def _group_by_key[Row: _Keyed](rows: Iterable[Row]) -> dict[str, list[Row]]:
    """As linhas de várias chaves, separadas por chave, pela ordem em que vieram."""
    grouped: dict[str, list[Row]] = defaultdict(list)
    for row in rows:
        grouped[row.key].append(row)
    return grouped


@contextmanager
def _timed(phase: str) -> Iterator[None]:
    """Quanto demorou cada fase, no log. É por onde se decide o que optimizar."""
    started = time.perf_counter()
    yield
    logger.info("%s: %.2fs", phase, time.perf_counter() - started)


def _parse_and_reconcile(
    files: Mapping[UploadSlot, tuple[IO[bytes], str]],
) -> ReconciliationResult:
    with _timed("leitura do POS list"):
        pos_list = parsers.parse_pos_list(*files[UploadSlot.POS_LIST])
    with _timed("leitura dos fechos SIMO"):
        closings = parsers.parse_simo_closings(*files[UploadSlot.SIMO_CLOSINGS])
    with _timed("leitura dos créditos Banka"):
        credits, banka_repeated = parsers.parse_banka_credits(*files[UploadSlot.BANKA_CREDITS])
    # O `NoClosingsError` já traz a mensagem em português: sobe tal como está.
    with _timed("reconciliação"):
        result = reconcile(pos_list, closings, credits)
    # Só interessam os repetidos de chaves com fecho: o resto do extracto não se valida.
    simo_keys = {detail.key for detail in result.details}
    result.summary.banka_repeated_movements = sum(
        count for key, count in banka_repeated.items() if key in simo_keys
    )
    return result
