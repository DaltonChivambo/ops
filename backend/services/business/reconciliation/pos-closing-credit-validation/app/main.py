"""Composition root do serviço `pos-closing-credit-validation`."""

from fastapi import FastAPI
from mozaops_libs.auth import register_audit

from app.controllers import error_handlers
from app.controllers.router import router
from app.settings import configure_logging

configure_logging()

app = FastAPI(title="MozaOps — pos-closing-credit-validation")

app.include_router(router)
error_handlers.register(app)
register_audit(app)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
