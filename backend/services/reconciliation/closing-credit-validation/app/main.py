"""Composition root do serviço `closing-credit-validation`.

Junta as peças e mais nada: a app, o router, os handlers de erro e o `/health`.
Quem decide o que recebe o quê é `controllers/dependencies.py`.

Sem Keycloak e sem CORS por agora — todas as rotas ficam abertas; fechar isto é
trabalho do M6+ e está registado no `ARCHITECTURE.md` §6.
"""

from fastapi import FastAPI

from app.controllers import error_handlers
from app.controllers.router import router

app = FastAPI(title="MozaOps — closing-credit-validation")

app.include_router(router)
error_handlers.register(app)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
