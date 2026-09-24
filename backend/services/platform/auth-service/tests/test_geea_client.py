"""O pedido que sai para o GEEA, ao nível do HTTP.

Os outros testes substituem o cliente por um duplo, e por isso nunca viam o
método nem os parâmetros. Foi assim que um GET passou nos testes e falhou no
GEEA real, que só aceita POST.
"""

import httpx
import pytest

from app.domain.errors import GeeaUnavailableError
from app.infrastructure.geea_client import GeeaClient

SSOLOGIN = "http://geea.test/geea/idmUtils/SSOLogin"


def _client(handler: httpx.MockTransport) -> GeeaClient:
    return GeeaClient(
        ssologin_url=SSOLOGIN,
        token_url="http://keycloak.test/auth/realms/QAS/protocol/openid-connect/token",
        realm="QAS",
        client_id="qa-mozaops",
        client_secret="segredo",
        transport=handler,
    )


async def test_login_is_a_post_with_the_credentials_in_the_query_string() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"output": {"accessToken": "token", "error": None}})

    output = await _client(httpx.MockTransport(handler)).login("m001926", "senha", "127.0.0.1")

    (request,) = seen
    assert request.method == "POST"
    assert dict(request.url.params) == {
        "realm": "QAS",
        "username": "m001926",
        "password": "senha",
        "clientId": "qa-mozaops",
        "clientSecret": "segredo",
        "clientIpAdress": "127.0.0.1",
    }
    assert request.content == b""
    assert output["accessToken"] == "token"


async def test_a_server_error_from_the_geea_is_unavailable_not_bad_credentials() -> None:
    """O que o GEEA real devolve a um GET: 500, e não 405."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"message": "Request method 'GET' not supported"})

    with pytest.raises(GeeaUnavailableError):
        await _client(httpx.MockTransport(handler)).login("m001926", "senha", "127.0.0.1")
