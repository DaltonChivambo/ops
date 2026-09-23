"""Caso de uso do caso de divergência: mudar-lhe o estado e o e-Ticket, e conciliá-lo."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from app.domain.e_ticket import normalize_e_ticket
from app.domain.errors import (
    InvalidCaseStatusError,
    InvalidMatchError,
    NotFoundError,
    NothingToUpdateError,
)
from app.domain.matching import (
    Match,
    MatchEffect,
    is_fully_matched,
    match_effect,
    reconciled_summary,
    validate_matches,
)
from app.domain.vocabulary import CaseStatus, CaseType, Validation
from app.infrastructure.tables import ClosingMatch, PendingCase
from app.repositories.case_repository import CaseRepository
from app.repositories.execution_repository import ExecutionRepository
from app.repositories.match_repository import MatchRepository
from app.services.match_sides import closing_side, movement_side

# O JSON usa hífens onde o enum usa underscores.
STATUS_FROM_JSON = {
    "pending": CaseStatus.PENDING,
    "in-review-internal": CaseStatus.IN_REVIEW_INTERNAL,
    "in-review-simo": CaseStatus.IN_REVIEW_SIMO,
    "resolved": CaseStatus.RESOLVED,
}


@dataclass(frozen=True, slots=True)
class ReconciledCase:
    """Uma chave depois de conciliada: o caso, as contagens, os pares, e o efeito no apuramento."""

    case: PendingCase
    # (nº de fechos SIMO, nº de movimentos Banka) da chave.
    counts: tuple[int, int]
    matches: list[ClosingMatch]
    before: MatchEffect
    after: MatchEffect


class CaseService:
    def __init__(
        self,
        cases: CaseRepository,
        executions: ExecutionRepository,
        matches: MatchRepository,
    ) -> None:
        self._cases = cases
        self._executions = executions
        self._matches = matches

    async def update(
        self, case_id: str, patch: dict[str, Any]
    ) -> tuple[PendingCase, dict[str, Any], tuple[int, int]]:
        """Actualiza estado/e-Ticket de um caso e recalcula o `summary` da execução."""
        data: dict[str, Any] = {}
        if "e_ticket" in patch:
            data["e_ticket"] = normalize_e_ticket(patch["e_ticket"])
        if "status" in patch:
            status = STATUS_FROM_JSON.get(patch["status"])
            if status is None:
                allowed = "», «".join(STATUS_FROM_JSON)
                raise InvalidCaseStatusError(
                    f"Estado de caso inválido: «{patch['status']}». "
                    f"Os estados possíveis são «{allowed}»."
                )
            data["status"] = status
            # O relógio do estado recomeça a cada mudança.
            data["status_since"] = date.today()
            data["resolved_at"] = date.today() if status is CaseStatus.RESOLVED else None

        if not data:
            raise NothingToUpdateError(
                "O pedido não indica nada para alterar. Envie o estado, o e-Ticket, ou ambos."
            )

        case = await self._cases.update(case_id, data)
        if case is None:
            raise NotFoundError("O caso indicado não existe.")

        counts = (1, 1)
        if case.type == CaseType.DUPLICATED:
            key_counts = await self._executions.count_by_key(case.execution_id, {case.key})
            counts = key_counts.get(case.key, (1, 1))

        return case, await self._refresh_counters(case.execution_id), counts

    async def reconcile(
        self, case_id: str, matches: Sequence[Match], matched_by: str | None
    ) -> tuple[ReconciledCase, dict[str, Any]]:
        """Guarda os pares fecho ↔ crédito de um caso de períodos repetidos."""
        case = await self._duplicated_case(case_id)
        outcome = await self._apply_matches(case, matches, matched_by)
        summary = await self._refresh_counters(
            case.execution_id, lambda current: _with_reconciliations(current, [outcome])
        )
        return outcome, summary

    async def reconcile_many(
        self,
        execution_id: str,
        requests: Sequence[tuple[str, Sequence[Match]]],
        matched_by: str | None,
    ) -> tuple[list[ReconciledCase], dict[str, Any]]:
        """Concilia vários casos de uma vez — todos ou nenhum."""
        if not requests:
            raise NothingToUpdateError("O pedido não traz nenhum caso para conciliar.")
        case_ids = [case_id for case_id, _ in requests]
        if len(set(case_ids)) != len(case_ids):
            raise InvalidMatchError("O mesmo caso vem mais do que uma vez no pedido.")

        outcomes: list[ReconciledCase] = []
        for case_id, matches in requests:
            case = await self._duplicated_case(case_id)
            if case.execution_id != execution_id:
                raise NotFoundError("Um dos casos indicados não pertence a esta execução.")
            try:
                outcomes.append(await self._apply_matches(case, matches, matched_by))
            except InvalidMatchError as error:
                raise InvalidMatchError(
                    f"POS {case.pos_id}, período {case.period}: {error.message}"
                ) from error

        summary = await self._refresh_counters(
            execution_id, lambda current: _with_reconciliations(current, outcomes)
        )
        return outcomes, summary

    async def _duplicated_case(self, case_id: str) -> PendingCase:
        case = await self._cases.find(case_id)
        if case is None:
            raise NotFoundError("O caso indicado não existe.")
        if case.type != CaseType.DUPLICATED:
            raise InvalidMatchError("Só os casos de períodos repetidos se conciliam fecho a fecho.")
        return case

    async def _apply_matches(
        self, case: PendingCase, matches: Sequence[Match], matched_by: str | None
    ) -> ReconciledCase:
        """Grava os pares de uma chave, muda o estado dos fechos e, se for o caso, regulariza."""
        execution_id = case.execution_id
        closings = await self._executions.list_details_by_key(execution_id, case.key)
        movements = await self._executions.list_movements_by_key(execution_id, case.key)
        closing_sides = [closing_side(row) for row in closings]
        movement_sides = [movement_side(row) for row in movements]
        validate_matches(matches, closing_sides, movement_sides)

        # Parte-se do estado dos fechos e não da lista de pares: um desalinhamento
        # acerta-se à próxima gravação em vez de ficar para sempre.
        currently_matched = {row.id for row in closings if row.validation == Validation.MATCH}
        previous = [
            Match(row.closing_id, row.movement_id)
            for row in await self._matches.list_by_key(execution_id, case.key)
            if row.closing_id in currently_matched
        ]
        rows = await self._matches.replace_for_key(execution_id, case.key, matches, matched_by)

        # Conciliado confere; sem par volta a período duplicado. Só os que mudaram.
        now_matched = {match.closing_id for match in matches}
        await self._executions.set_closings_validation(
            execution_id, now_matched - currently_matched, Validation.MATCH, Decimal(0)
        )
        await self._executions.set_closings_validation(
            execution_id, currently_matched - now_matched, Validation.DUPLICATED, None
        )

        if is_fully_matched(matches, closing_sides) and case.status != CaseStatus.RESOLVED:
            today = date.today()
            await self._cases.update(
                case.id,
                {"status": CaseStatus.RESOLVED, "status_since": today, "resolved_at": today},
            )

        return ReconciledCase(
            case=case,
            counts=(len(closings), len(movements)),
            matches=rows,
            before=match_effect(previous, closing_sides, movement_sides),
            after=match_effect(matches, closing_sides, movement_sides),
        )

    async def _refresh_counters(
        self,
        execution_id: str,
        adjust: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Reflecte no `summary` guardado as contagens de casos abertos/regularizados."""
        execution = await self._executions.find(execution_id)
        if execution is None:
            raise NotFoundError("A execução indicada não existe ou já foi removida.")

        summary = dict(execution.summary or {})
        if adjust is not None:
            summary = adjust(summary)
        counts = await self._cases.count_by_status(execution_id)
        resolved = counts.get(CaseStatus.RESOLVED, 0)
        # camelCase: são as chaves do documento JSONB, não atributos de Python.
        summary["resolvedCases"] = resolved
        summary["openCases"] = sum(counts.values()) - resolved
        # Recontados a partir dos fechos: acertar por diferenças deixava dinheiro
        # numa linha sem fechos.
        duplicated = await self._executions.duplicated_totals(execution_id)
        if duplicated is not None:
            count, simo, banka = duplicated
            summary["duplicatedPeriods"] = count
            summary["simoAmountDuplicated"] = float(simo)
            summary["bankaAmountDuplicated"] = float(banka)
        await self._executions.save_summary(execution_id, summary)
        return summary


def _with_reconciliations(
    summary: dict[str, Any], outcomes: Sequence[ReconciledCase]
) -> dict[str, Any]:
    """O `summary` com o efeito de cada chave conciliada, uma a seguir à outra."""
    for outcome in outcomes:
        summary = reconciled_summary(summary, outcome.before, outcome.after)
    return summary
