"""HTTP da conciliação fecho a fecho: o que se pode conciliar, e conciliar — um caso ou vários.

Conciliar declara «este crédito pagou este fecho», e todas as rotas que o fazem
registam quem o disse. Os pares vão sempre inteiros, e por isso as escritas são
PUT: mandar o mesmo conjunto duas vezes deixa tudo como mandá-lo uma.
"""

from fastapi import APIRouter

from app.controllers.dependencies import CaseServiceDep, CurrentUser, ValidationServiceDep
from app.controllers.schemas import (
    CaseReconciliationIn,
    CaseReconciliationOut,
    ClosingMatchOut,
    KeyBreakdownOut,
    PendingCaseOut,
    ReconciliationBatchIn,
    ReconciliationBatchOut,
)

router = APIRouter()


@router.get("/execucoes/{execution_id}/conciliacoes")
async def list_reconciliation_candidates(
    execution_id: str, service: ValidationServiceDep
) -> list[KeyBreakdownOut]:
    """Os casos de períodos duplicados por tratar que têm créditos, com os pares sugeridos."""
    period_end, candidates = await service.list_reconciliation_candidates(execution_id)
    return [
        KeyBreakdownOut.from_parts(
            period_end,
            candidate.case.key,
            candidate.closings,
            candidate.movements,
            candidate.case,
            candidate.matches,
            candidate.suggested_matches,
        )
        for candidate in candidates
    ]


@router.put("/execucoes/{execution_id}/conciliacoes")
async def reconcile_cases(
    execution_id: str,
    body: ReconciliationBatchIn,
    service: CaseServiceDep,
    user: CurrentUser,
) -> ReconciliationBatchOut:
    requests = [(item.case_id, item.to_matches()) for item in body.items]
    outcomes, summary = await service.reconcile_many(execution_id, requests, user.username)
    return ReconciliationBatchOut(
        cases=[PendingCaseOut.from_row(outcome.case, *outcome.counts) for outcome in outcomes],
        summary=summary,
    )


@router.put("/casos/{case_id}/conciliacao")
async def reconcile_case(
    case_id: str,
    body: CaseReconciliationIn,
    service: CaseServiceDep,
    user: CurrentUser,
) -> CaseReconciliationOut:
    outcome, summary = await service.reconcile(case_id, body.to_matches(), user.username)
    return CaseReconciliationOut(
        case=PendingCaseOut.from_row(outcome.case, *outcome.counts),
        summary=summary,
        matches=[ClosingMatchOut.from_match(row) for row in outcome.matches],
    )
