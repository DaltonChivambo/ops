"""O `/me` — a fonte de verdade das áreas para o SPA."""

import time

from tests.conftest import make_token


class TestComTokenValido:
    def test_devolve_quem_esta_do_outro_lado(self, client):
        response = client.get("/identity/me", headers={"Authorization": f"Bearer {make_token()}"})

        assert response.status_code == 200
        body = response.json()
        assert body["username"] == "m001926"
        assert body["departmentCode"] == "3230"
        assert body["function"] == "Director"
        assert body["areas"] == ["canais"]

    def test_quem_nao_esta_no_mapa_entra_sem_areas(self, client):
        """Autenticar não é ser autorizado: entra, e a aplicação nega tudo."""
        token = make_token(preferred_username="m009999", departmentCode="1600", function="Técnico")

        response = client.get("/identity/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json()["areas"] == []

    def test_a_funcao_nao_muda_o_que_se_abre(self, client):
        """Um técnico da mesma unidade vê exactamente o que o director vê."""
        token = make_token(preferred_username="m007000", function="Técnico")

        response = client.get("/identity/me", headers={"Authorization": f"Bearer {token}"})
        assert response.json()["areas"] == ["canais"]


class TestSemTokenValido:
    def test_sem_cabecalho_da_401_no_envelope(self, client):
        response = client.get("/identity/me")

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthenticated"
        assert response.headers["www-authenticate"] == "Bearer"

    def test_token_expirado(self, client):
        agora = int(time.time())
        token = make_token(iat=agora - 7200, exp=agora - 3600)

        response = client.get("/identity/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401

    def test_token_de_outro_cliente_do_banco(self, client):
        response = client.get(
            "/identity/me",
            headers={"Authorization": f"Bearer {make_token(azp='qa-workflow-ui')}"},
        )
        assert response.status_code == 401

    def test_lixo(self, client):
        """Nunca 500: um cabeçalho inventado é um pedido inválido, não uma avaria."""
        response = client.get("/identity/me", headers={"Authorization": "Bearer nao-e-um-jwt"})
        assert response.status_code == 401


def test_health_nao_pede_token(client):
    assert client.get("/health").status_code == 200
