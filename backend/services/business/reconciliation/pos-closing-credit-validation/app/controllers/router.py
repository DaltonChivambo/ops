"""Junta os controladores sob o prefixo da automação.

O prefixo não leva `/api`: essa é a fronteira da API, não parte do caminho. Em
produção é o Traefik que a corta (`stripprefix`), em desenvolvimento é o
`proxy.conf.json` do Angular — mesma topologia dos dois lados.
"""

from fastapi import APIRouter, Depends

from app.controllers import cases, executions, reconciliations, settings
from app.controllers.dependencies import require_access

# A autenticação está aqui, no router inteiro, e não rota a rota: uma rota
# acrescentada amanhã nasce fechada. Exige-se a área da automação, ou a
# concessão deste microserviço — ver `dependencies.py`.
router = APIRouter(
    prefix="/pos/validacao-credito-fecho",
    dependencies=[Depends(require_access)],
)
router.include_router(executions.router)
router.include_router(cases.router)
router.include_router(reconciliations.router)
router.include_router(settings.router)
