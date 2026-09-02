"""Junta os controladores sob o prefixo da automação.

O prefixo não leva `/api`: essa é a fronteira da API, não parte do caminho. Em
produção é o Traefik que a corta (`stripprefix`), em desenvolvimento é o
`proxy.conf.json` do Angular — mesma topologia dos dois lados.
"""

from fastapi import APIRouter

from app.controllers import cases, executions

router = APIRouter(prefix="/pos/validacao-credito-fecho")
router.include_router(executions.router)
router.include_router(cases.router)
