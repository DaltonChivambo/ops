"""Dependências da API v1: sessão, utilizador autenticado, repositórios, publisher.

Único sítio onde a camada `api/` liga o FastAPI ao resto. Os controllers importam daqui,
nunca de `infrastructure/`.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ops_common.auth import CurrentUser
from ops_common.http import ParametrosPagina, parametros_pagina

from notification.core.security import get_auth
from notification.infrastructure.persistence.session import get_session

_auth = get_auth()
get_current_user = _auth.get_current_user
require_roles = _auth.require_roles


async def get_db() -> AsyncIterator[AsyncSession]:
    async for sessao in get_session():
        yield sessao


def get_publisher(request: Request):
    """O publisher vive no `app.state`, aberto uma vez no lifespan."""
    return request.app.state.publisher


Db = Annotated[AsyncSession, Depends(get_db)]
Utilizador = Annotated[CurrentUser, Depends(get_current_user)]
Paginacao = Annotated[ParametrosPagina, Depends(parametros_pagina)]
