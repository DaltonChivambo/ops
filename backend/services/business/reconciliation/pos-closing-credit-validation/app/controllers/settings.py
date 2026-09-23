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
    # Muda o que todos vêem como atrasado, execuções antigas incluídas; fica registado quem mexeu.
    user: CurrentUser,
) -> SlaSettingsOut:
    # O documento vem inteiro: «aviso menor que prazo» não se valida por partes.
    saved = await service.save(body.case_sla_days, body.case_warning_days, user.username)
    return SlaSettingsOut.from_row(saved)
