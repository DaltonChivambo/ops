"""Composition root do serviço `identity`.

Junta as peças e mais nada: a app, o router, os handlers de erro e o `/health`.
Quem decide o que recebe o quê é `controllers/dependencies.py`.
"""

from fastapi import FastAPI

from app.controllers import error_handlers
from app.controllers.router import router
from app.settings import configure_logging

configure_logging()

app = FastAPI(title="MozaOps — identity")

app.include_router(router)
error_handlers.register(app)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
