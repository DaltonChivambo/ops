"""O contrato HTTP das sessões: o que sai, com que estado, e o que não sai."""

import logging

from app.controllers.sessions import REFRESH_COOKIE
from app.settings import Settings, settings


class TestLogin:
    def test_credenciais_certas_abrem_sessao(self, client):
        response = client.post(
            "/identity/sessions", json={"username": "m001926", "password": "senha-certa"}
        )

        assert response.status_code == 200
        body = response.json()
        assert body["accessToken"]
        assert body["expiresIn"] == 18000
        assert body["principal"]["username"] == "m001926"
        assert body["principal"]["department"] == "Departamento de Apoio Operacional"

    def test_papeis_vem_do_nosso_mapa_e_nao_do_token(self, client):
        """O token só traz `work_queue`; quem decide `supervisor` somos nós."""
        response = client.post(
            "/identity/sessions", json={"username": "m001926", "password": "senha-certa"}
        )
        assert sorted(response.json()["principal"]["roles"]) == ["operator", "supervisor"]

    def test_token_de_renovacao_vai_em_cookie_inacessivel_ao_javascript(self, client):
        response = client.post(
            "/identity/sessions", json={"username": "m001926", "password": "senha-certa"}
        )

        cookie = response.headers["set-cookie"]
        assert REFRESH_COOKIE in cookie
        assert "HttpOnly" in cookie
        assert "SameSite=lax" in cookie.replace("samesite", "SameSite")
        assert f"Path={settings.session_cookie_path}" in cookie

    def test_o_cookie_fica_limitado_a_fronteira_da_api_deste_servico(self):
        """O valor por omissão, que é o que vale em produção.

        Os testes correm com `Path=/` porque falam com o serviço sem o proxy à
        frente; sem esta afirmação, alguém podia deixar `/` no compose e o
        cookie passava a acompanhar os pedidos às automações.

        Lê-se o valor declarado, e não `Settings()`, que aqui traria o do
        ambiente de teste.
        """
        assert Settings.model_fields["session_cookie_path"].default == "/api/identity"

    def test_o_cookie_exige_https_por_omissao(self):
        assert Settings.model_fields["session_cookie_secure"].default is True

    def test_o_token_de_renovacao_nao_vai_no_corpo(self, client):
        """Se fosse no corpo, ficava ao alcance de qualquer script na página."""
        body = client.post(
            "/identity/sessions", json={"username": "m001926", "password": "senha-certa"}
        ).json()
        assert "refreshToken" not in body
        assert "refresh-valido" not in str(body)

    def test_credenciais_erradas_dao_401_no_envelope(self, client):
        response = client.post(
            "/identity/sessions", json={"username": "m001926", "password": "errada"}
        )

        assert response.status_code == 401
        assert response.json() == {
            "error": {
                "code": "invalid_credentials",
                "message": "Credenciais inválidas. Verifique o utilizador e a password.",
            }
        }

    def test_utilizador_inexistente_responde_o_mesmo_que_password_errada(self, client):
        """Distinguir os dois casos confirmaria contas a quem as adivinha."""
        inexistente = client.post(
            "/identity/sessions", json={"username": "nao-existe", "password": "x"}
        )
        errada = client.post("/identity/sessions", json={"username": "m001926", "password": "x"})
        assert inexistente.json() == errada.json()
        assert inexistente.status_code == errada.status_code


class TestPasswordNaoEscapa:
    def test_nao_aparece_na_resposta_de_erro_de_validacao(self, client):
        """O 422 do FastAPI devolveria o corpo do pedido — com a password."""
        response = client.post("/identity/sessions", json={"username": "m001926"})

        assert response.status_code == 422
        assert "password" not in response.text.lower()

    def test_nao_aparece_nos_logs(self, client, caplog):
        with caplog.at_level(logging.DEBUG):
            client.post(
                "/identity/sessions",
                json={"username": "m001926", "password": "s3nh4-mesmo-secreta"},
            )

        assert "s3nh4-mesmo-secreta" not in caplog.text


class TestLimiteDeTentativas:
    def test_ao_fim_de_n_tentativas_responde_429(self, client):
        for _ in range(10):
            client.post("/identity/sessions", json={"username": "m001926", "password": "errada"})

        response = client.post(
            "/identity/sessions", json={"username": "m001926", "password": "senha-certa"}
        )
        assert response.status_code == 429
        assert response.json()["error"]["code"] == "too_many_attempts"

    def test_o_limite_e_por_utilizador(self, client):
        for _ in range(10):
            client.post("/identity/sessions", json={"username": "m001926", "password": "e"})

        outra = client.post("/identity/sessions", json={"username": "m004410", "password": "e"})
        assert outra.status_code == 401


class TestRenovacao:
    def test_renova_a_partir_do_cookie(self, client):
        client.post("/identity/sessions", json={"username": "m001926", "password": "senha-certa"})

        response = client.post("/identity/sessions/refresh")
        assert response.status_code == 200
        assert response.json()["accessToken"]

    def test_sem_cookie_nao_ha_o_que_renovar(self, client):
        response = client.post("/identity/sessions/refresh")
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthenticated"


class TestLogout:
    def test_apaga_o_cookie(self, client):
        client.post("/identity/sessions", json={"username": "m001926", "password": "senha-certa"})

        response = client.delete("/identity/sessions")
        assert response.status_code == 204
        assert client.post("/identity/sessions/refresh").status_code == 401


class TestGeeaEmBaixo:
    def test_responde_503_e_nao_credenciais_invalidas(self, client, geea):
        """O problema é nosso; mandar a pessoa reescrever a password não ajuda."""
        from app.domain.errors import GeeaUnavailableError

        geea.raises = GeeaUnavailableError()
        response = client.post(
            "/identity/sessions", json={"username": "m001926", "password": "senha-certa"}
        )

        assert response.status_code == 503
        assert response.json()["error"]["code"] == "identity_unavailable"
