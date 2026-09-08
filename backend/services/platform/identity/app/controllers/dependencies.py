"""A cablagem do pedido. É aqui, e só aqui, que se diz quem recebe o quê."""

from typing import Annotated

from fastapi import Depends

from app.infrastructure.auth import auth, role_mapping, verifier
from app.infrastructure.geea_client import GeeaClient
from app.services.session_service import AttemptLimiter, SessionService
from app.settings import settings
from mozaops_libs.auth import Principal

# Uma instância só, para a janela de tentativas ser partilhada entre pedidos —
# um limitador criado por pedido não limitava nada.
_limiter = AttemptLimiter(settings.login_attempts_per_minute)

_geea = GeeaClient(
    ssologin_url=settings.geea_ssologin_url,
    token_url=settings.geea_token_url,
    realm=settings.geea_realm,
    client_id=settings.geea_client_id,
    client_secret=settings.geea_client_secret,
)


def get_session_service() -> SessionService:
    return SessionService(_geea, verifier, role_mapping, _limiter)


SessionServiceDep = Annotated[SessionService, Depends(get_session_service)]
CurrentPrincipal = Annotated[Principal, Depends(auth.principal)]
