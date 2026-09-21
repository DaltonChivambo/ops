"""Quem sou eu — a fonte de verdade das áreas, para o SPA.

O frontend não pode decidir isto sozinho: o SPA guarda o token, não o abre, e
as áreas não são uma claim que se copie — saem dos papéis do cliente no realm
somados ao mapa de unidades, e quem os junta é o backend. Esta rota é o que faz
com que dar acesso a mais alguém seja mexer no realm ou na configuração, e não
publicar um SPA novo.
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
