"""Único mapeamento exceção → status HTTP deste serviço.

Sem este ficheiro aparecem `HTTPException` espalhados pelos `services/` e o FastAPI volta a
infiltrar-se nas camadas de baixo.
"""

from __future__ import annotations

from fastapi import FastAPI

from ops_common.http import register_error_handlers


def registar_error_handlers(app: FastAPI) -> None:
    register_error_handlers(app)
