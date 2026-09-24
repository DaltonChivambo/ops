"""O único ficheiro que conhece o contrato do `SSOLogin` do GEEA."""

import logging
from typing import Any

import httpx

from app.domain.errors import GeeaUnavailableError, InvalidCredentialsError

logger = logging.getLogger("auth-service")


class GeeaClient:
    def __init__(
        self,
        *,
        ssologin_url: str,
        token_url: str,
        realm: str,
        client_id: str,
        client_secret: str,
        timeout: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self._ssologin_url = ssologin_url
        self._token_url = token_url
        self._realm = realm
        self._client_id = client_id
        self._client_secret = client_secret
        self._timeout = timeout
        self._transport = transport

    async def login(self, username: str, password: str, client_ip: str) -> dict[str, Any]:
        """Troca credenciais por tokens. Devolve o bloco `output` do GEEA.

        POST com os parâmetros na query string e o corpo vazio: é o contrato do
        GEEA real, que recusa GET com 500 («Request method 'GET' not supported»).
        """
        params = {
            "realm": self._realm,
            "username": username,
            "password": password,
            "clientId": self._client_id,
            "clientSecret": self._client_secret,
            "clientIpAdress": client_ip,
        }

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout, transport=self._transport
            ) as client:
                response = await client.post(self._ssologin_url, params=params)
        except httpx.HTTPError as exc:
            # Sem `exc`: o httpx põe o URL na mensagem, e o URL leva a password.
            logger.warning("SSOLogin inacessível em %s: %s", self._ssologin_url, type(exc).__name__)
            raise GeeaUnavailableError from None

        if response.status_code in (400, 401, 403):
            raise InvalidCredentialsError
        if response.status_code >= 400:
            logger.warning("SSOLogin devolveu %s", response.status_code)
            raise GeeaUnavailableError

        return self._output_of(response)

    async def refresh(self, refresh_token: str) -> dict[str, Any]:
        """Renova pelo endpoint normal do Keycloak, e não pelo wrapper."""
        form = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self._client_id,
            "client_secret": self._client_secret,
        }

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout, transport=self._transport
            ) as client:
                response = await client.post(self._token_url, data=form)
        except httpx.HTTPError as exc:
            logger.warning(
                "Endpoint de token inacessível em %s: %s", self._token_url, type(exc).__name__
            )
            raise GeeaUnavailableError from None

        if response.status_code in (400, 401, 403):
            raise InvalidCredentialsError
        if response.status_code >= 400:
            raise GeeaUnavailableError

        payload = self._json(response)
        # A rota OIDC responde snake_case e o wrapper camelCase.
        return {
            "accessToken": payload.get("access_token"),
            "refreshToken": payload.get("refresh_token"),
            "expiresIn": str(payload.get("expires_in", "")),
            "refreshExpiresIn": str(payload.get("refresh_expires_in", "")),
            "tokenType": payload.get("token_type", "bearer"),
        }

    def _json(self, response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError:
            logger.warning(
                "GEEA respondeu %s sem JSON (content-type %s)",
                response.status_code,
                response.headers.get("content-type", "?"),
            )
            raise GeeaUnavailableError from None
        if not isinstance(payload, dict):
            logger.warning("GEEA respondeu JSON que não é objecto: %s", type(payload).__name__)
            raise GeeaUnavailableError
        return payload

    def _output_of(self, response: httpx.Response) -> dict[str, Any]:
        payload = self._json(response)
        output = payload.get("output")
        if not isinstance(output, dict):
            # Só os nomes dos campos: os valores podem trazer tokens.
            logger.warning("SSOLogin sem bloco `output`; campos: %s", sorted(payload))
            raise GeeaUnavailableError

        # O GEEA responde 200 com o erro lá dentro.
        if output.get("error"):
            raise InvalidCredentialsError
        if not output.get("accessToken"):
            logger.warning("SSOLogin sem `accessToken` no `output`; campos: %s", sorted(output))
            raise GeeaUnavailableError

        return output
