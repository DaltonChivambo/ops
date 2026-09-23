"""HTTP das execuções: correr uma validação e consultar o que ela produziu."""

import os
from typing import Any

from fastapi import APIRouter, File, Query, Response, UploadFile
from fastapi.responses import StreamingResponse

from app.controllers.dependencies import ValidationServiceDep
from app.controllers.schemas import (
    ClosingDetailOut,
    DetailCountsOut,
    DetailsPageOut,
    KeyBreakdownOut,
    SimoDuplicatesIn,
    ValidationResultOut,
)
from app.domain.errors import InvalidInputError, UploadTooLargeError
from app.domain.vocabulary import SLOT_LABELS, RepeatedClosings, UploadSlot
from app.pagination import parse_page
from app.settings import settings

router = APIRouter()

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

REQUIRED_SLOTS = tuple(UploadSlot)


@router.post("/execucoes", status_code=201)
async def create_execution(
    service: ValidationServiceDep,
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

    # Sem os `None`: o `missing` acima garantiu que não há nenhum.
    present = {slot: upload for slot, upload in uploads.items() if upload is not None}
    _reject_oversized(present)
    files = {slot: (present[slot].file, present[slot].filename or slot) for slot in REQUIRED_SLOTS}

    execution_id = await service.run(files)
    execution = await service.get_execution(execution_id)
    cases, key_counts = await service.list_cases(execution_id)
    return ValidationResultOut.from_row(execution, cases, key_counts)


def _reject_oversized(uploads: dict[UploadSlot, UploadFile]) -> None:
    """Trava os ficheiros grandes demais ANTES de o openpyxl lhes tocar."""
    limit = settings.max_upload_mb * 1024 * 1024
    sizes = {slot: _size_of(upload) for slot, upload in uploads.items()}
    oversized = [(slot, upload) for slot, upload in uploads.items() if sizes[slot] > limit]
    if not oversized:
        return

    slot, upload = oversized[0]
    megabytes = sizes[slot] / 1024 / 1024
    raise UploadTooLargeError(
        f"O ficheiro «{upload.filename or SLOT_LABELS[slot]}» no campo «{SLOT_LABELS[slot]}» "
        f"tem {megabytes:.1f} MB e excede o limite de {settings.max_upload_mb} MB. "
        "Exporte um período mais curto e volte a submeter."
    )


def _size_of(upload: UploadFile) -> int:
    """O tamanho, mesmo sem comprimento no multipart. O corpo já está recebido."""
    if upload.size is not None:
        return upload.size

    stream = upload.file
    stream.seek(0, os.SEEK_END)
    size = stream.tell()
    stream.seek(0)
    return size


@router.get("/execucoes/ultima", response_model=ValidationResultOut | None)
async def get_latest_execution(service: ValidationServiceDep) -> Any:
    execution = await service.get_latest_execution()
    if execution is None:
        # 204 e não 200 com `null`: distingue «ainda não correu» de «sem resultado».
        return Response(status_code=204)
    cases, key_counts = await service.list_cases(execution.id)
    return ValidationResultOut.from_row(execution, cases, key_counts)


@router.put("/execucoes/{execution_id}/duplicados-simo")
async def set_simo_duplicates(
    execution_id: str,
    body: SimoDuplicatesIn,
    service: ValidationServiceDep,
) -> ValidationResultOut:
    """Conta, ou deixa de contar, os fechos repetidos do export da SIMO."""
    await service.set_count_simo_duplicates(execution_id, body.counted)
    execution = await service.get_execution(execution_id)
    cases, key_counts = await service.list_cases(execution_id)
    return ValidationResultOut.from_row(execution, cases, key_counts)


@router.get("/execucoes/{execution_id}/detalhes")
async def list_details(
    execution_id: str,
    service: ValidationServiceDep,
    page: int | None = Query(default=None),
    per_page: int | None = Query(default=None, alias="perPage"),
    validation: str | None = Query(default=None),
    q: str | None = Query(default=None),
    # Marca que se cruza com todos os estados: `all`, `only` ou `without`.
    repeated: RepeatedClosings = Query(default=RepeatedClosings.ALL),
) -> DetailsPageOut:
    await service.get_execution(execution_id)  # 404 se não existir
    parsed_page = parse_page(page, per_page)
    result = await service.list_details(execution_id, parsed_page, validation, q, repeated)
    return DetailsPageOut(
        items=[
            ClosingDetailOut.from_row(detail, *result.key_counts.get(detail.key, (1, 1)))
            for detail in result.details
        ],
        page=parsed_page.page,
        per_page=parsed_page.per_page,
        total=result.total,
        counts=DetailCountsOut(**result.counts) if result.counts is not None else None,
    )


@router.get("/execucoes/{execution_id}/chaves/{key}")
async def get_key_breakdown(
    execution_id: str, key: str, service: ValidationServiceDep
) -> KeyBreakdownOut:
    """Os dois lados de uma chave — o que a tabela abre ao clicar num fecho."""
    breakdown = await service.get_key_breakdown(execution_id, key)
    return KeyBreakdownOut.from_parts(
        breakdown["key"],
        breakdown["closings"],
        breakdown["movements"],
        breakdown["case"],
        breakdown["matches"],
        breakdown["suggested_matches"],
    )


@router.get("/execucoes/{execution_id}/relatorio")
async def download_report(execution_id: str, service: ValidationServiceDep) -> StreamingResponse:
    content, filename = await service.build_report(execution_id)
    return StreamingResponse(
        iter([content]),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
