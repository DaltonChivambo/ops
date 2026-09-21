"""O `/me` — a fonte de verdade das áreas para o SPA."""

import time

from tests.conftest import AZP, make_token


class TestWithValidToken:
    def test_returns_the_caller(self, client):
        response = client.get(
            "/auth-service/me", headers={"Authorization": f"Bearer {make_token()}"}
        )

        assert response.status_code == 200
        body = response.json()
        assert body["username"] == "m001926"
        assert body["departmentCode"] == "3230"
        assert body["function"] == "Director"
        assert body["areas"] == ["channels"]

    def test_unmapped_user_gets_no_areas(self, client):
        """Autenticar não é ser autorizado: entra, e a aplicação nega tudo."""
        token = make_token(preferred_username="m009999", departmentCode="1600", function="Técnico")

        response = client.get("/auth-service/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json()["areas"] == []

    def test_client_roles_open_their_areas(self, client):
        """O realm provisiona, e a unidade deixa de ser precisa.

        É o caso de quem está registado no departamento inteiro: sem isto,
        entrava e não via nada.
        """
        token = make_token(
            preferred_username="m009999",
            departmentCode="2350",
            resource_access={AZP: {"roles": ["channels"]}},
        )

        response = client.get("/auth-service/me", headers={"Authorization": f"Bearer {token}"})
        assert response.json()["areas"] == ["channels"]

    def test_the_all_areas_role_travels_as_is(self, client):
        """O SPA é que o reconhece, por isso não se expande aqui."""
        token = make_token(resource_access={AZP: {"roles": ["all-areas"]}})

        response = client.get("/auth-service/me", headers={"Authorization": f"Bearer {token}"})
        assert response.json()["areas"] == ["all-areas", "channels"]

    def test_job_function_does_not_change_access(self, client):
        """Um técnico da mesma unidade vê exactamente o que o director vê."""
        token = make_token(preferred_username="m007000", function="Técnico")

        response = client.get("/auth-service/me", headers={"Authorization": f"Bearer {token}"})
        assert response.json()["areas"] == ["channels"]


class TestWithoutValidToken:
    def test_missing_header_returns_401_in_envelope(self, client):
        response = client.get("/auth-service/me")

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthenticated"
        assert response.headers["www-authenticate"] == "Bearer"

    def test_expired_token(self, client):
        now = int(time.time())
        token = make_token(iat=now - 7200, exp=now - 3600)

        response = client.get("/auth-service/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401

    def test_token_from_another_bank_client(self, client):
        response = client.get(
            "/auth-service/me",
            headers={"Authorization": f"Bearer {make_token(azp='qa-workflow-ui')}"},
        )
        assert response.status_code == 401

    def test_garbage(self, client):
        """Nunca 500: um cabeçalho inventado é um pedido inválido, não uma avaria."""
        response = client.get("/auth-service/me", headers={"Authorization": "Bearer nao-e-um-jwt"})
        assert response.status_code == 401


def test_health_does_not_require_token(client):
    assert client.get("/health").status_code == 200
