"""Junta os controladores sob o prefixo do serviço."""

from fastapi import APIRouter, Depends

from app.controllers import me, sessions
from app.infrastructure.auth import auth

# O aberto é a excepção: abrir sessão acontece antes de haver token.
public = APIRouter()
public.include_router(sessions.router)

protected = APIRouter(dependencies=[Depends(auth.principal)])
protected.include_router(me.router)

router = APIRouter(prefix="/auth-service")
router.include_router(public)
router.include_router(protected)
