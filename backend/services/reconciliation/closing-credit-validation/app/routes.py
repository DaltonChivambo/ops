"""Camada de apresentação — rotas HTTP do módulo.

Porte de `controllers.py` do MozaOps v1: mesmo prefixo e mesmos sub-caminhos
(em português, herdados da v1) para o frontend já existente falar com este
serviço sem alterações — só o alvo do proxy de dev muda. Sem BD, sem
openpyxl: só valida o pedido e chama `service.py`.
"""
from typing import Any

from fastapi import APIRouter, Depends, Query, Request, Response, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from . import serializers, service
from .database import get_session
from .errors import BusinessError
from .pagination import parse_page

router = APIRouter(prefix="/pos/validacao-credito-fecho")

REQUIRED_SLOTS = ("posList", "simoClosings", "bankaCredits")
SLOT_LABELS = {
    "posList": "Lista de POS",
    "simoClosings": "Fechos SIMO",
    "bankaCredits": "Créditos Banka",
}


@router.post("/execucoes", status_code=201)
async def create_execution(
    posList: UploadFile | None = None,
    simoClosings: UploadFile | None = None,
    bankaCredits: UploadFile | None = None,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    uploads = {"posList": posList, "simoClosings": simoClosings, "bankaCredits": bankaCredits}
    missing = [slot for slot in REQUIRED_SLOTS if uploads[slot] is None]
    if missing:
        raise BusinessError(
            "Faltam ficheiros para executar a validação: "
            + ", ".join(f"«{SLOT_LABELS[slot]}»" for slot in missing)
            + ". Carregue os três ficheiros e volte a submeter."
        )

    files = {
        slot: (uploads[slot].file, uploads[slot].filename or slot) for slot in REQUIRED_SLOTS
    }
    execution_id = await service.run_validation(session, files)
    execution = await service.get_execution(session, execution_id)
    cases = await service.list_cases(session, execution_id)
    return serializers.execution_to_dict(execution, cases)


@router.get("/execucoes/ultima")
async def get_latest_execution(session: AsyncSession = Depends(get_session)) -> Response:
    execution = await service.get_latest_execution(session)
    if execution is None:
        return Response(status_code=204)
    cases = await service.list_cases(session, execution.id)
    return JSONResponse(serializers.execution_to_dict(execution, cases))


@router.get("/execucoes/{execution_id}/detalhes")
async def list_details(
    execution_id: str,
    page: int | None = Query(default=None),
    perPage: int | None = Query(default=None),
    validation: str | None = Query(default=None),
    q: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    await service.get_execution(session, execution_id)  # 404 se não existir
    parsed_page = parse_page(page, perPage)
    details, total, counts = await service.list_details(
        session, execution_id, parsed_page, validation, q
    )
    return {
        "items": [serializers.detail_to_dict(detail) for detail in details],
        "total": total,
        "page": parsed_page.page,
        "perPage": parsed_page.perPage,
        "counts": counts,
    }


@router.get("/execucoes/{execution_id}/chaves/{key}")
async def get_key_breakdown(
    execution_id: str, key: str, session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    """Os dois lados de uma chave — o que a tabela abre ao clicar num fecho."""
    breakdown = await service.get_key_breakdown(session, execution_id, key)
    return serializers.key_breakdown_to_dict(breakdown)


@router.patch("/casos/{case_id}")
async def update_case(
    case_id: str, request: Request, session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    try:
        patch = await request.json()
    except Exception:  # noqa: BLE001 — corpo vazio/inválido, tratado como "nada a mudar"
        patch = {}
    case, summary = await service.update_case(session, case_id, patch or {})
    return {"case": serializers.case_to_dict(case), "summary": summary}


@router.get("/execucoes/{execution_id}/relatorio")
async def download_report(
    execution_id: str, session: AsyncSession = Depends(get_session)
) -> StreamingResponse:
    content, filename = await service.build_report(session, execution_id)
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
