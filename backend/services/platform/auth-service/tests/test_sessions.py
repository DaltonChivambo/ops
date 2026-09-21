"""O contrato HTTP das sessões: o que sai, com que estado, e o que não sai."""

import logging

from app.controllers.sessions import REFRESH_COOKIE
from app.settings import Settings, settings
from tests.conftest import CLIENT


class TestLogin:
    def test_valid_credentials_open_session(self, client):
        response = client.post(
            "/auth-service/sessions", json={"username": "m001926", "password": "senha-certa"}
        )

        assert response.status_code == 200
        body = response.json()
        assert body["accessToken"]
        assert body["expiresIn"] == 18000
        assert body["principal"]["username"] == "m001926"
        assert body["principal"]["department"] == "Canais e Serviços de Integração"

    def test_roles_come_from_our_map_not_the_token(self, client):
        """O token só traz `work_queue`; quem decide `supervisor` somos nós."""
        response = client.post(
            "/auth-service/sessions", json={"username": "m001926", "password": "senha-certa"}
        )
        assert response.json()["principal"]["areas"] == ["channels"]

    def test_refresh_token_goes_in_httponly_cookie(self, client):
        response = client.post(
            "/auth-service/sessions", json={"username": "m001926", "password": "senha-certa"}
        )

        cookie = response.headers["set-cookie"]
        assert REFRESH_COOKIE in cookie
        assert "HttpOnly" in cookie
        assert "SameSite=lax" in cookie.replace("samesite", "SameSite")
        assert f"Path={settings.session_cookie_path}" in cookie

    def test_cookie_is_scoped_to_this_service_api_boundary(self):
        """O valor por omissão, que é o que vale em produção.

        Os testes correm com `Path=/` porque falam com o serviço sem o proxy à
        frente; sem esta afirmação, alguém podia deixar `/` no compose e o
        cookie passava a acompanhar os pedidos às automações.

        Lê-se o valor declarado, e não `Settings()`, que aqui traria o do
        ambiente de teste.
        """
        assert Settings.model_fields["session_cookie_path"].default == "/api/auth-service"

    def test_cookie_requires_https_by_default(self):
        assert Settings.model_fields["session_cookie_secure"].default is True

    def test_refresh_token_is_not_in_body(self, client):
        """Se fosse no corpo, ficava ao alcance de qualquer script na página."""
        body = client.post(
            "/auth-service/sessions", json={"username": "m001926", "password": "senha-certa"}
        ).json()
        assert "refreshToken" not in body
        assert "refresh-valido" not in str(body)

    def test_wrong_credentials_return_401_in_envelope(self, client):
        response = client.post(
            "/auth-service/sessions", json={"username": "m001926", "password": "wrong"}
        )

        assert response.status_code == 401
        assert response.json() == {
            "error": {
                "code": "invalid_credentials",
                "message": "Credenciais inválidas. Verifique o utilizador e a password.",
            }
        }

    def test_unknown_user_responds_same_as_wrong_password(self, client):
        """Distinguir os dois casos confirmaria contas a quem as adivinha."""
        unknown = client.post(
            "/auth-service/sessions", json={"username": "nao-existe", "password": "x"}
        )
        wrong = client.post("/auth-service/sessions", json={"username": "m001926", "password": "x"})
        assert unknown.json() == wrong.json()
        assert unknown.status_code == wrong.status_code


class TestWithoutArea:
    """Autenticar não é ser autorizado: sem área nenhuma, nem sessão há."""

    def test_login_without_area_returns_invalid_credentials(self, client, geea):
        geea.valid["m009999"] = "senha-certa"
        geea.claims_by_user["m009999"] = {
            "departmentCode": "1600",
            "department": "Direcção qualquer",
            "function": "Técnico",
        }

        response = client.post(
            "/auth-service/sessions", json={"username": "m009999", "password": "senha-certa"}
        )

        # A mesma mensagem e o mesmo código de sempre — distinguir «autenticou
        # mas não tem acesso» de «não autenticou» confirmaria, a quem tenta
        # adivinhar contas, que esta existe.
        assert response.status_code == 401
        assert response.json() == {
            "error": {
                "code": "invalid_credentials",
                "message": "Credenciais inválidas. Verifique o utilizador e a password.",
            }
        }

    def test_service_access_alone_is_enough_to_get_in(self, client, geea):
        """Quem tem uma automação concedida entra, mesmo sem área nenhuma.

        É por aqui que entra um programa que integra connosco, ou alguém que
        consulta uma automação sem lhe mexer.
        """
        geea.valid["api-validacao-dsti"] = "senha-certa"
        geea.claims_by_user["api-validacao-dsti"] = {
            "departmentCode": "",
            "resource_access": {CLIENT: {"roles": ["service:pos-fechos:read"]}},
        }

        response = client.post(
            "/auth-service/sessions",
            json={"username": "api-validacao-dsti", "password": "senha-certa"},
        )

        assert response.status_code == 200
        assert response.json()["principal"]["areas"] == []

    def test_login_without_area_leaves_no_cookie(self, client, geea):
        geea.valid["m009999"] = "senha-certa"
        geea.claims_by_user["m009999"] = {"departmentCode": "1600"}

        response = client.post(
            "/auth-service/sessions", json={"username": "m009999", "password": "senha-certa"}
        )

        assert "set-cookie" not in response.headers

    def test_refresh_for_user_who_lost_area_also_fails(self, client, geea):
        """A unidade pode deixar de mapear a área entre o login e a renovação —
        o cookie continua válido, e o `/refresh` é onde isso se apanha."""
        client.post(
            "/auth-service/sessions", json={"username": "m001926", "password": "senha-certa"}
        )

        geea.refresh_claims = {"departmentCode": "1600"}
        response = client.post("/auth-service/sessions/refresh")

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "invalid_credentials"


class TestPasswordDoesNotLeak:
    def test_not_in_validation_error_response(self, client):
        """O 422 do FastAPI devolveria o corpo do pedido — com a password."""
        response = client.post("/auth-service/sessions", json={"username": "m001926"})

        assert response.status_code == 422
        assert "password" not in response.text.lower()

    def test_not_in_logs(self, client, caplog):
        with caplog.at_level(logging.DEBUG):
            client.post(
                "/auth-service/sessions",
                json={"username": "m001926", "password": "s3nh4-mesmo-secreta"},
            )

        assert "s3nh4-mesmo-secreta" not in caplog.text


class TestAttemptLimit:
    def test_after_n_attempts_responds_429(self, client):
        for _ in range(10):
            client.post("/auth-service/sessions", json={"username": "m001926", "password": "wrong"})

        response = client.post(
            "/auth-service/sessions", json={"username": "m001926", "password": "senha-certa"}
        )
        assert response.status_code == 429
        assert response.json()["error"]["code"] == "too_many_attempts"

    def test_limit_is_per_user(self, client):
        for _ in range(10):
            client.post("/auth-service/sessions", json={"username": "m001926", "password": "e"})

        other = client.post("/auth-service/sessions", json={"username": "m004410", "password": "e"})
        assert other.status_code == 401


class TestRefresh:
    def test_refreshes_from_cookie(self, client):
        client.post(
            "/auth-service/sessions", json={"username": "m001926", "password": "senha-certa"}
        )

        response = client.post("/auth-service/sessions/refresh")
        assert response.status_code == 200
        assert response.json()["accessToken"]

    def test_without_cookie_nothing_to_refresh(self, client):
        response = client.post("/auth-service/sessions/refresh")
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthenticated"


class TestLogout:
    def test_clears_the_cookie(self, client):
        client.post(
            "/auth-service/sessions", json={"username": "m001926", "password": "senha-certa"}
        )

        response = client.delete("/auth-service/sessions")
        assert response.status_code == 204
        assert client.post("/auth-service/sessions/refresh").status_code == 401


class TestGeeaDown:
    def test_responds_503_not_invalid_credentials(self, client, geea):
        """O problema é nosso; mandar a pessoa reescrever a password não ajuda."""
        from app.domain.errors import GeeaUnavailableError

        geea.raises = GeeaUnavailableError()
        response = client.post(
            "/auth-service/sessions", json={"username": "m001926", "password": "senha-certa"}
        )

        assert response.status_code == 503
        assert response.json()["error"]["code"] == "identity_unavailable"
