"""Quem sou eu — a fonte de verdade dos papéis, para o SPA.

O frontend não pode decidir isto sozinho: os papéis do MozaOps não estão no
token do GEEA, são decididos por nós. Esta rota é o que faz com que mudar o
mapa de papéis seja mudar configuração do backend, e não publicar um SPA novo.
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
        roles=sorted(principal.roles),
        department_code=principal.department_code,
        department=principal.department,
        function=principal.function,
    )
