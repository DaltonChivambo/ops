"""HTTP das execuções: correr uma validação e consultar o que ela produziu.

Sub-caminhos em português, herdados do MozaOps v1 — é o contrato que o SPA já
consome, e o `ARCHITECTURE.md` §7 regista-o como a excepção assumida à regra de
tudo o resto ser em inglês.

Sem base de dados e sem openpyxl aqui: valida o pedido, chama o serviço,
devolve o que ele deu.
"""

from typing import Any

from fastapi import APIRouter, File, Query, Response, UploadFile
from fastapi.responses import StreamingResponse

from app.controllers.dependencies import ValidationServiceDep, Writer
from app.controllers.schemas import (
    ClosingDetailOut,
    DetailCountsOut,
    DetailsPageOut,
    KeyBreakdownOut,
    ValidationResultOut,
)
from app.domain.errors import InvalidInputError, UploadTooLargeError
from app.domain.vocabulary import SLOT_LABELS, UploadSlot
from app.pagination import parse_page
from app.settings import settings

router = APIRouter()

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

REQUIRED_SLOTS = tuple(UploadSlot)


@router.post("/execucoes", status_code=201)
async def create_execution(
    service: ValidationServiceDep,
    # Correr uma validação escreve — não é para quem só audita.
    _writer: Writer,
    # Os `alias` são os nomes dos campos no formulário — contrato com o SPA.
    pos_list: UploadFile | None = File(default=None, alias="posList"),
    simo_closings: UploadFile | None = File(default=None, alias="simoClosings"),
    banka_credits: UploadFile | None = File(default=None, alias="bankaCredits"),
) -> ValidationResultOut:
    uploads = {
        UploadSlot.POS_LIST: pos_list,
        UploadSlot.SIMO_CLOSINGS: simo_closings,
        UploadSlot.BANKA_CREDITS: banka_credits,
    }
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
    _reject_oversized(present)
    files = {slot: (present[slot].file, present[slot].filename or slot) for slot in REQUIRED_SLOTS}

    execution_id = await service.run(files)
    execution = await service.get_execution(execution_id)
    cases = await service.list_cases(execution_id)
    return ValidationResultOut.from_row(execution, cases)


def _reject_oversized(uploads: dict[UploadSlot, UploadFile]) -> None:
    """Trava os ficheiros grandes demais ANTES de o openpyxl lhes tocar.

    O `max_upload_mb` estava declarado desde o início e nunca era lido: na
    prática não havia limite nenhum, e um ficheiro suficientemente grande punha
    o worker a mastigar memória até o pedido morrer sem explicação. Falhar aqui
    custa um cabeçalho e dá ao operador uma frase que ele percebe.
    """
    limite = settings.max_upload_mb * 1024 * 1024
    grandes = [
        (slot, upload)
        for slot, upload in uploads.items()
        if upload.size is not None and upload.size > limite
    ]
    if not grandes:
        return

    slot, upload = grandes[0]
    megabytes = (upload.size or 0) / 1024 / 1024
    raise UploadTooLargeError(
        f"O ficheiro «{upload.filename or SLOT_LABELS[slot]}» no campo «{SLOT_LABELS[slot]}» "
        f"tem {megabytes:.1f} MB e excede o limite de {settings.max_upload_mb} MB. "
        "Exporte um período mais curto e volte a submeter."
    )


@router.get("/execucoes/ultima", response_model=ValidationResultOut | None)
async def get_latest_execution(service: ValidationServiceDep) -> Any:
    execution = await service.get_latest_execution()
    if execution is None:
        # 204 e não 200 com `null`: é assim que o SPA distingue «ainda não correu
        # nada» de «correu e não deu resultado».
        return Response(status_code=204)
    cases = await service.list_cases(execution.id)
    return ValidationResultOut.from_row(execution, cases)


@router.get("/execucoes/{execution_id}/detalhes")
async def list_details(
    execution_id: str,
    service: ValidationServiceDep,
    page: int | None = Query(default=None),
    per_page: int | None = Query(default=None, alias="perPage"),
    validation: str | None = Query(default=None),
    q: str | None = Query(default=None),
) -> DetailsPageOut:
    await service.get_execution(execution_id)  # 404 se não existir
    parsed_page = parse_page(page, per_page)
    details, total, counts = await service.list_details(execution_id, parsed_page, validation, q)
    return DetailsPageOut(
        items=[ClosingDetailOut.from_row(detail) for detail in details],
        total=total,
        page=parsed_page.page,
        per_page=parsed_page.per_page,
        counts=DetailCountsOut(**counts),
    )


@router.get("/execucoes/{execution_id}/chaves/{key}")
async def get_key_breakdown(
    execution_id: str, key: str, service: ValidationServiceDep
) -> KeyBreakdownOut:
    """Os dois lados de uma chave — o que a tabela abre ao clicar num fecho."""
    breakdown = await service.get_key_breakdown(execution_id, key)
    return KeyBreakdownOut.from_parts(
        breakdown["key"], breakdown["closings"], breakdown["movements"], breakdown["case"]
    )


@router.get("/execucoes/{execution_id}/relatorio")
async def download_report(execution_id: str, service: ValidationServiceDep) -> StreamingResponse:
    content, filename = await service.build_report(execution_id)
    return StreamingResponse(
        iter([content]),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
