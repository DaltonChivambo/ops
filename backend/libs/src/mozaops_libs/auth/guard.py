"""A guarda das rotas: quem está do outro lado, e se pode o que está a pedir."""

from collections.abc import Awaitable, Callable

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from mozaops_libs.auth.access import AccessLevel
from mozaops_libs.auth.areas import AreaMapping
from mozaops_libs.auth.errors import ForbiddenError, UnauthenticatedError
from mozaops_libs.auth.principal import Principal, principal_from_claims
from mozaops_libs.auth.verifier import TokenVerifier

# `auto_error=False`: sem isto o FastAPI responde fora do nosso envelope.
_bearer = HTTPBearer(auto_error=False)


class Auth:
    """Construída uma vez, no arranque do serviço, a partir da configuração."""

    def __init__(self, verifier: TokenVerifier, mapping: AreaMapping, client: str):
        self._verifier = verifier
        self._mapping = mapping
        self._client = client

    async def principal(
        self,
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    ) -> Principal:
        if credentials is None or not credentials.credentials:
            raise UnauthenticatedError

        claims = await self._verifier.verify(credentials.credentials)
        principal = principal_from_claims(claims, self._mapping, self._client)
        # É daqui que o middleware de auditoria tira o principal.
        request.state.principal = principal
        return principal

    def require_access(self, service: str, area: str) -> Callable[..., Awaitable[Principal]]:
        """Dependência que exige acesso a um microserviço."""

        async def guard(
            request: Request, principal: Principal = Depends(self.principal)
        ) -> Principal:
            required = AccessLevel.required_for(request.method)
            if not principal.is_allowed(service, area, required):
                raise ForbiddenError
            return principal

        return guard
