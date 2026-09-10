"""HTTP das definições da automação — hoje, só o prazo de tratamento."""

from fastapi import APIRouter

from app.controllers.dependencies import CurrentUser, SettingsServiceDep
from app.controllers.schemas import SlaSettingsIn, SlaSettingsOut

router = APIRouter()


@router.get("/definicoes")
async def get_settings(service: SettingsServiceDep) -> SlaSettingsOut:
    return SlaSettingsOut.from_row(await service.get())


@router.put("/definicoes")
async def save_settings(
    body: SlaSettingsIn,
    service: SettingsServiceDep,
    # Mudar o prazo muda o que toda a gente vê como atrasado, incluindo em
    # execuções antigas. Continua a ser de quem for da área — como o resto —
    # mas fica registado quem mexeu.
    user: CurrentUser,
) -> SlaSettingsOut:
    # O documento vem inteiro, e não em pedaços: o «aviso tem de ser menor do
    # que o prazo» não se valida com metade dos campos à frente.
    saved = await service.save(body.case_sla_days, body.case_warning_days, user.username)
    return SlaSettingsOut.from_row(saved)
