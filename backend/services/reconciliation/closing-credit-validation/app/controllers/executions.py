"""HTTP das execuções: correr uma validação e consultar o que ela produziu.

Sub-caminhos em português, herdados do MozaOps v1 — é o contrato que o SPA já
consome, e o `ARCHITECTURE.md` §7 regista-o como a excepção assumida à regra de
tudo o resto ser em inglês.

Sem base de dados e sem openpyxl aqui: valida o pedido, chama o serviço,
devolve o que ele deu.
"""

from typing import Any

from fastapi import APIRouter, Query, Response, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from app.controllers import serializers
from app.controllers.dependencies import ValidationServiceDep
from app.domain.errors import InvalidInputError
from app.pagination import parse_page

router = APIRouter()

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

REQUIRED_SLOTS = ("posList", "simoClosings", "bankaCredits")
SLOT_LABELS = {
    "posList": "Lista de POS",
    "simoClosings": "Fechos SIMO",
    "bankaCredits": "Créditos Banka",
}


@router.post("/execucoes", status_code=201)
async def create_execution(
    service: ValidationServiceDep,
    posList: UploadFile | None = None,
    simoClosings: UploadFile | None = None,
    bankaCredits: UploadFile | None = None,
) -> dict[str, Any]:
    uploads = {"posList": posList, "simoClosings": simoClosings, "bankaCredits": bankaCredits}
    missing = [slot for slot in REQUIRED_SLOTS if uploads[slot] is None]
    if missing:
        raise InvalidInputError(
            "Faltam ficheiros para executar a validação: "
            + ", ".join(f"«{SLOT_LABELS[slot]}»" for slot in missing)
            + ". Carregue os três ficheiros e volte a submeter."
        )

    # Reconstruído sem os `None` — o `missing` acima já garantiu que não há nenhum,
    # mas é aqui que o tipo passa a dizê-lo.
    present = {slot: upload for slot, upload in uploads.items() if upload is not None}
    files = {slot: (present[slot].file, present[slot].filename or slot) for slot in REQUIRED_SLOTS}

    execution_id = await service.run(files)
    execution = await service.get_execution(execution_id)
    cases = await service.list_cases(execution_id)
    return serializers.execution_to_dict(execution, cases)


@router.get("/execucoes/ultima")
async def get_latest_execution(service: ValidationServiceDep) -> Response:
    execution = await service.get_latest_execution()
    if execution is None:
        # 204 e não 200 com `null`: é assim que o SPA distingue «ainda não correu
        # nada» de «correu e não deu resultado».
        return Response(status_code=204)
    cases = await service.list_cases(execution.id)
    return JSONResponse(serializers.execution_to_dict(execution, cases))


@router.get("/execucoes/{execution_id}/detalhes")
async def list_details(
    execution_id: str,
    service: ValidationServiceDep,
    page: int | None = Query(default=None),
    perPage: int | None = Query(default=None),
    validation: str | None = Query(default=None),
    q: str | None = Query(default=None),
) -> dict[str, Any]:
    await service.get_execution(execution_id)  # 404 se não existir
    parsed_page = parse_page(page, perPage)
    details, total, counts = await service.list_details(execution_id, parsed_page, validation, q)
    return {
        "items": [serializers.detail_to_dict(detail) for detail in details],
        "total": total,
        "page": parsed_page.page,
        "perPage": parsed_page.perPage,
        "counts": counts,
    }


@router.get("/execucoes/{execution_id}/chaves/{key}")
async def get_key_breakdown(
    execution_id: str, key: str, service: ValidationServiceDep
) -> dict[str, Any]:
    """Os dois lados de uma chave — o que a tabela abre ao clicar num fecho."""
    breakdown = await service.get_key_breakdown(execution_id, key)
    return serializers.key_breakdown_to_dict(breakdown)


@router.get("/execucoes/{execution_id}/relatorio")
async def download_report(execution_id: str, service: ValidationServiceDep) -> StreamingResponse:
    content, filename = await service.build_report(execution_id)
    return StreamingResponse(
        iter([content]),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
