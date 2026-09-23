"""Quem sou eu — a fonte de verdade das áreas, para o SPA."""

from fastapi import APIRouter

from app.controllers.dependencies import CurrentPrincipal
from app.controllers.schemas import PrincipalResponse

router = APIRouter(tags=["auth-service"])


@router.get("/me", response_model=PrincipalResponse)
async def me(principal: CurrentPrincipal) -> PrincipalResponse:
    return PrincipalResponse(
        subject=principal.subject,
        username=principal.username,
        name=principal.name,
        email=principal.email,
        areas=sorted(principal.areas),
        service_access={
            service: level.name.lower() for service, level in principal.service_access.items()
        },
        department_code=principal.department_code,
        department=principal.department,
        function=principal.function,
    )
