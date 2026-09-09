"""HTTP dos casos de divergência: o que o operador muda enquanto os trata."""

from fastapi import APIRouter

from app.controllers.dependencies import CaseServiceDep
from app.controllers.schemas import CasePatchIn, CaseUpdateOut, PendingCaseOut

router = APIRouter()


@router.patch("/casos/{case_id}")
async def update_case(
    case_id: str,
    service: CaseServiceDep,
    # Marcar um caso como regularizado declara «este dinheiro está apurado» e a
    # data vai para o relatório do departamento. É o acto com mais significado
    # do sistema — e, hoje, é de quem for da área, como o resto: dentro da área
    # não há graus. Quem guarda a porta é o router.
    patch: CasePatchIn | None = None,
) -> CaseUpdateOut:
    # Corpo ausente trata-se como «nada a mudar»: é o serviço que decide o que
    # responder a isso, e responde o mesmo que a um `{}`.
    campos = patch.model_dump(exclude_unset=True) if patch else {}
    case, summary = await service.update(case_id, campos)
    return CaseUpdateOut(case=PendingCaseOut.from_row(case), summary=summary)
