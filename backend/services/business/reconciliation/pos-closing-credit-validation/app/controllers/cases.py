"""HTTP dos casos de divergência: o que o operador muda enquanto os trata."""

from fastapi import APIRouter

from app.controllers.dependencies import CaseServiceDep
from app.controllers.schemas import CasePatchIn, CaseUpdateOut, PendingCaseOut

router = APIRouter()


@router.patch("/casos/{case_id}")
async def update_case(
    case_id: str,
    service: CaseServiceDep,
    # Dentro da área não há graus; quem guarda a porta é o router.
    patch: CasePatchIn | None = None,
) -> CaseUpdateOut:
    # Corpo ausente é «nada a mudar», como um `{}`.
    fields = patch.model_dump(exclude_unset=True) if patch else {}
    case, summary, counts = await service.update(case_id, fields)
    return CaseUpdateOut(case=PendingCaseOut.from_row(case, *counts), summary=summary)
