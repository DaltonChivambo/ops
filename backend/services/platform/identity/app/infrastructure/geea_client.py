"""O único ficheiro que conhece o contrato do `SSOLogin` do GEEA.

Está isolado de propósito. O `SSOLogin` é uma API legada que leva as
credenciais na query string de um `GET`; no dia em que a equipa de IAM
registar o MozaOps como aplicação, o login passa a ser um reencaminhamento
para o ecrã do banco e **este ficheiro desaparece inteiro** — o resto do
serviço, que só lida com o JWT que sai daqui, não dá por isso.

Duas cautelas que não são detalhe:

- O `httpx` regista o URL de cada pedido, e este URL leva a password. O
  silenciamento está em `settings.configure_logging`, e é lá que está a razão.
- Nada nesta camada guarda a password: entra como argumento, sai no pedido, e
  o objecto que a carregava morre com a função.
"""

import logging
from typing import Any

import httpx

from app.domain.errors import GeeaUnavailableError, InvalidCredentialsError

logger = logging.getLogger("identity")


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
    ):
        self._ssologin_url = ssologin_url
        self._token_url = token_url
        self._realm = realm
        self._client_id = client_id
        self._client_secret = client_secret
        self._timeout = timeout

    async def login(self, username: str, password: str, client_ip: str) -> dict[str, Any]:
        """Troca credenciais por tokens. Devolve o bloco `output` do GEEA."""
        params = {
            "realm": self._realm,
            "username": username,
            "password": password,
            "clientId": self._client_id,
            "clientSecret": self._client_secret,
            "clientIpAdress": client_ip,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(self._ssologin_url, params=params)
        except httpx.HTTPError as exc:
            # Sem `exc` na mensagem: o `httpx` põe o URL — e a password — na
            # representação de várias das suas excepções.
            logger.warning("SSOLogin inacessível: %s", type(exc).__name__)
            raise GeeaUnavailableError from None

        if response.status_code in (400, 401, 403):
            raise InvalidCredentialsError
        if response.status_code >= 400:
            logger.warning("SSOLogin devolveu %s", response.status_code)
            raise GeeaUnavailableError

        return self._output_of(response)

    async def refresh(self, refresh_token: str) -> dict[str, Any]:
        """Renova pelo endpoint normal do Keycloak, e não pelo wrapper.

        O `SSOLogin` devolve um `refreshToken` mas não tem por onde o trocar:
        quem o aceita é o realm, na rota padrão do OIDC.
        """
        form = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self._client_id,
            "client_secret": self._client_secret,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(self._token_url, data=form)
        except httpx.HTTPError as exc:
            logger.warning("Endpoint de token inacessível: %s", type(exc).__name__)
            raise GeeaUnavailableError from None

        if response.status_code in (400, 401, 403):
            raise InvalidCredentialsError
        if response.status_code >= 400:
            raise GeeaUnavailableError

        payload = self._json(response)
        # A rota padrão do OIDC responde em snake_case; o wrapper responde em
        # camelCase. Traduz-se aqui, para o resto do serviço ver uma forma só.
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
            raise GeeaUnavailableError from None
        if not isinstance(payload, dict):
            raise GeeaUnavailableError
        return payload

    def _output_of(self, response: httpx.Response) -> dict[str, Any]:
        payload = self._json(response)
        output = payload.get("output")
        if not isinstance(output, dict):
            raise GeeaUnavailableError

        # O GEEA responde 200 com o erro lá dentro; um 200 não chega para
        # concluir que o login correu bem.
        if output.get("error"):
            raise InvalidCredentialsError
        if not output.get("accessToken"):
            raise GeeaUnavailableError

        return output
