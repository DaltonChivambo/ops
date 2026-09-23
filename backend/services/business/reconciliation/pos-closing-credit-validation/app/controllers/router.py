"""Junta os controladores sob o prefixo da automação."""

from fastapi import APIRouter, Depends

from app.controllers import cases, executions, reconciliations, settings
from app.controllers.dependencies import require_access

# A autenticação está no router inteiro: uma rota nova nasce fechada.
# Exige a área da automação ou a concessão deste microserviço — ver `dependencies.py`.
router = APIRouter(
    prefix="/pos/validacao-credito-fecho",
    dependencies=[Depends(require_access)],
)
router.include_router(executions.router)
router.include_router(cases.router)
router.include_router(reconciliations.router)
router.include_router(settings.router)
