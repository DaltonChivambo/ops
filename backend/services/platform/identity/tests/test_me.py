"""O `/me` — a fonte de verdade das áreas para o SPA."""

import time

from tests.conftest import make_token


class TestWithValidToken:
    def test_returns_the_caller(self, client):
        response = client.get("/identity/me", headers={"Authorization": f"Bearer {make_token()}"})

        assert response.status_code == 200
        body = response.json()
        assert body["username"] == "m001926"
        assert body["departmentCode"] == "3230"
        assert body["function"] == "Director"
        assert body["areas"] == ["channels"]

    def test_unmapped_user_gets_no_areas(self, client):
        """Autenticar não é ser autorizado: entra, e a aplicação nega tudo."""
        token = make_token(preferred_username="m009999", departmentCode="1600", function="Técnico")

        response = client.get("/identity/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json()["areas"] == []

    def test_job_function_does_not_change_access(self, client):
        """Um técnico da mesma unidade vê exactamente o que o director vê."""
        token = make_token(preferred_username="m007000", function="Técnico")

        response = client.get("/identity/me", headers={"Authorization": f"Bearer {token}"})
        assert response.json()["areas"] == ["channels"]


class TestWithoutValidToken:
    def test_missing_header_returns_401_in_envelope(self, client):
        response = client.get("/identity/me")

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthenticated"
        assert response.headers["www-authenticate"] == "Bearer"

    def test_expired_token(self, client):
        now = int(time.time())
        token = make_token(iat=now - 7200, exp=now - 3600)

        response = client.get("/identity/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401

    def test_token_from_another_bank_client(self, client):
        response = client.get(
            "/identity/me",
            headers={"Authorization": f"Bearer {make_token(azp='qa-workflow-ui')}"},
        )
        assert response.status_code == 401

    def test_garbage(self, client):
        """Nunca 500: um cabeçalho inventado é um pedido inválido, não uma avaria."""
        response = client.get("/identity/me", headers={"Authorization": "Bearer nao-e-um-jwt"})
        assert response.status_code == 401


def test_health_does_not_require_token(client):
    assert client.get("/health").status_code == 200
