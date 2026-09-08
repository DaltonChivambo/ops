"""Quem sou eu — a fonte de verdade das áreas, para o SPA.

O frontend não pode decidir isto sozinho: as áreas do MozaOps não estão no
token do GEEA, são decididas por nós. Esta rota é o que faz com que abrir uma
área a mais uma unidade seja mudar configuração do backend, e não publicar um
SPA novo.
"""

from fastapi import APIRouter

from app.controllers.dependencies import CurrentPrincipal
from app.controllers.schemas import PrincipalResponse

router = APIRouter(tags=["identity"])


@router.get("/me", response_model=PrincipalResponse)
async def me(principal: CurrentPrincipal) -> PrincipalResponse:
    return PrincipalResponse(
        subject=principal.subject,
        username=principal.username,
        name=principal.name,
        email=principal.email,
        areas=sorted(principal.areas),
        department_code=principal.department_code,
        department=principal.department,
        function=principal.function,
    )
