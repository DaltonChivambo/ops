"""HTTP dos casos de divergência: o que o operador muda enquanto os trata."""

from typing import Any

from fastapi import APIRouter, Request

from app.controllers import serializers
from app.controllers.dependencies import CaseServiceDep

router = APIRouter()


@router.patch("/casos/{case_id}")
async def update_case(case_id: str, request: Request, service: CaseServiceDep) -> dict[str, Any]:
    try:
        patch = await request.json()
    # Corpo vazio ou mal formado trata-se como «nada a mudar»: a resposta que o
    # operador merece é a mesma, e o serviço é que decide o que fazer com isso.
    except Exception:  # noqa: BLE001
        patch = {}
    case, summary = await service.update(case_id, patch or {})
    return {"case": serializers.case_to_dict(case), "summary": summary}
