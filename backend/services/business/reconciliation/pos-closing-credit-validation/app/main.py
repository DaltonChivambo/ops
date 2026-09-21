"""Composition root do serviço `pos-closing-credit-validation`.

Junta as peças e mais nada: a app, o router, os handlers de erro e o `/health`.
Quem decide o que recebe o quê é `controllers/dependencies.py`.

As rotas exigem um token válido do GEEA — a exigência está no router inteiro,
em `controllers/router.py`, para que uma rota nova nasça fechada. O `/health`
fica de fora: quem o consulta é o Docker, e não tem sessão nenhuma.

Sem CORS: o SPA e a API partilham origem, por desenho (Traefik à frente).
"""

from fastapi import FastAPI

from app.controllers import error_handlers
from app.controllers.router import router
from app.settings import configure_logging
from mozaops_libs.auth import register_audit

configure_logging()

app = FastAPI(title="MozaOps — pos-closing-credit-validation")

app.include_router(router)
error_handlers.register(app)
register_audit(app)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
