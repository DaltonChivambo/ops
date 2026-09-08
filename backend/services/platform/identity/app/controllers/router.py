"""Junta os controladores sob o prefixo do serviço.

O prefixo não leva `/api`: essa é a fronteira da API, não parte do caminho. Em
produção corta-a o Traefik (`stripprefix`), em desenvolvimento o
`proxy.conf.json` do Angular — mesma topologia dos dois lados.
"""

from fastapi import APIRouter

from app.controllers import me, sessions

router = APIRouter(prefix="/identity")
router.include_router(sessions.router)
router.include_router(me.router)
