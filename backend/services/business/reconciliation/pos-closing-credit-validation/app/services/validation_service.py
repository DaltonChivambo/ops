"""Caso de uso da validação: executar, consultar e gerar o relatório.

O pipeline está deliberadamente separado em `parse → reconcile → persist`: hoje
corre síncrono dentro do pedido HTTP, mas a separação já deixa a porta aberta
para o desenho assíncrono sem tocar no pipeline em si.

Esta camada não sabe o que é um pedido HTTP nem uma tabela: recebe repositórios
e devolve objectos. Quem os transforma em JSON é o controlador.
"""

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import IO, Any, Protocol

from app.domain.errors import NotFoundError
from app.domain.matching import Match, is_fully_matched, suggest_matches
from app.domain.models import ReconciliationResult
from app.domain.reconciliation import reconcile
from app.domain.vocabulary import CaseType, UploadSlot, Validation
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


@dataclass(frozen=True, slots=True)
class DetailsPage:
    """Uma página da tabela de fechos, com o que cada linha precisa além do fecho."""

    details: list[ClosingDetail]
    total: int
    # Contagens dos filtros, sobre a execução inteira — não sobre a página.
    counts: dict[str, int]
    # (nº de fechos SIMO, nº de movimentos Banka) das chaves duplicadas da página.
    key_counts: dict[str, tuple[int, int]]
    # (nº, montante) dos créditos sem fecho por analisar, das chaves da página que os têm.
    unmatched_by_key: dict[str, tuple[int, Decimal]]


@dataclass(frozen=True, slots=True)
class ReconciliationCandidate:
    """Um caso de períodos duplicados com tudo o que é preciso para o conciliar."""

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
        """Executa a validação e devolve o id da execução persistida.

        `files` mapeia cada campo multipart para `(stream, nome do ficheiro)`.
        """
        result = _parse_and_reconcile(files)
        names = {slot: files[slot][1] for slot in UploadSlot}
        return await self._executions.create(result, names, result.summary.to_json_dict())

    async def get_execution(self, execution_id: str) -> Execution:
        execution = await self._executions.find(execution_id)
        if execution is None:
            raise NotFoundError("A execução indicada não existe ou já foi removida.")
        return execution

    async def get_latest_execution(self) -> Execution | None:
        return await self._executions.find_latest()

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
        unmatched_credits_only: bool = False,
    ) -> DetailsPage:
        details, total = await self._executions.list_details(
            execution_id, page, validation, search, unmatched_credits_only
        )
        counts = await self._executions.count_details_by_validation(execution_id, search)
        duplicated_keys = {
            detail.key for detail in details if detail.validation == Validation.DUPLICATED
        }
        return DetailsPage(
            details=details,
            total=total,
            counts=counts,
            key_counts=await self._executions.count_by_key(execution_id, duplicated_keys),
            unmatched_by_key=await self._executions.unmatched_credits_by_key(
                execution_id, {detail.key for detail in details}
            ),
        )

    async def get_key_breakdown(self, execution_id: str, key: str) -> dict[str, Any]:
        """Os dois lados de uma chave: os fechos da SIMO e os movimentos do Banka.

        A unidade é a CHAVE e não o fecho, porque o crédito do Banka é da chave: um
        fecho isolado não tem crédito próprio de que se possa falar. Clicar num fecho
        abre a chave a que ele pertence.
        """
        execution = await self.get_execution(execution_id)  # 404 se a execução não existir
        details = await self._executions.list_details_by_key(execution_id, key)
        if not details:
            raise NotFoundError("Não há nenhum fecho com esta chave nesta execução.")
        movements = await self._executions.list_movements_by_key(execution_id, key)
        return {
            "period_end": execution.period_end,
            "key": key,
            "closings": details,
            "movements": movements,
            "case": await self._cases.find_by_key(execution_id, key),
            # O que já foi conciliado, e o que se pode conciliar só pelo valor. A
            # sugestão vai sempre: é o ecrã que decide onde a mostra, e a regra
            # do par fica num sítio só (`domain/matching.py`).
            "matches": await self._matches.list_by_key(execution_id, key),
            "suggested_matches": suggest_matches(
                [closing_side(row) for row in details],
                [movement_side(row) for row in movements],
            ),
        }

    async def list_reconciliation_candidates(
        self, execution_id: str
    ) -> tuple[date, list[ReconciliationCandidate]]:
        """As chaves que se conciliam com crédito igual — cada fecho com um crédito do mesmo valor.

        Só essas: uma chave onde algum fecho não tem crédito igual não se concilia
        aqui, trata-se pelo caso (fase e e-Ticket). Também ficam de fora as que já
        têm pares guardados — alguém lhes mexeu no painel, e confirmar a
        sugestão por cima desfazia esse trabalho.

        Três queries para todos os casos, e não três por caso: numa execução com
        centenas de chaves duplicadas o pedido não pode crescer com elas.

        Vai com o último dia do intervalo, para o ecrã separar os créditos que
        sobram dos que já são do intervalo seguinte.
        """
        execution = await self.get_execution(execution_id)  # 404 se a execução não existir
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
        return execution.period_end, candidates

    async def build_report(self, execution_id: str) -> tuple[bytes, str]:
        """Gera o .xlsx da execução a partir do que está persistido."""
        execution = await self.get_execution(execution_id)
        details = await self._executions.list_all_details(execution_id)
        cases = await self._cases.list_by_execution(execution_id)
        return report.build_workbook(execution, details, cases), f"{execution.report_name}.xlsx"


class _Keyed(Protocol):
    # Propriedade e não atributo: nas tabelas `key` é um `Mapped[str]`, que só
    # vira `str` quando lido — e é isso que interessa aqui.
    @property
    def key(self) -> str: ...


def _group_by_key[Row: _Keyed](rows: Iterable[Row]) -> dict[str, list[Row]]:
    """As linhas de várias chaves, separadas por chave, pela ordem em que vieram."""
    grouped: dict[str, list[Row]] = defaultdict(list)
    for row in rows:
        grouped[row.key].append(row)
    return grouped


def _parse_and_reconcile(
    files: Mapping[UploadSlot, tuple[IO[bytes], str]],
) -> ReconciliationResult:
    pos_list = parsers.parse_pos_list(*files[UploadSlot.POS_LIST])
    closings = parsers.parse_simo_closings(*files[UploadSlot.SIMO_CLOSINGS])
    credits, banka_discarded = parsers.parse_banka_credits(*files[UploadSlot.BANKA_CREDITS])
    # O `NoClosingsError` é uma excepção de negócio do PDD, com a mensagem já em
    # português: sobe tal como está, sem tradução pelo meio.
    result = reconcile(pos_list, closings, credits)
    # Quem sabe das linhas repetidas é o parser; o domínio só recebe créditos
    # limpos. O número vai para o `summary`, para o operador saber que o
    # ficheiro vinha com elas.
    result.summary.banka_duplicates_discarded = banka_discarded
    return result
