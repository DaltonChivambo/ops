"""As rotas estão fechadas — e é este ficheiro que o prova.

Ao contrário do `conftest.py`, aqui **não** se substitui a autenticação: o
cliente é a aplicação como ela responde em produção. Se alguém acrescentar uma
rota fora do router, ou tirar a dependência do router, é aqui que se vê.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.controllers.dependencies import get_case_service, get_validation_service
from app.infrastructure.auth import auth
from app.main import app
from app.settings import settings
from mozaops_libs.auth import AccessLevel, Principal
from tests.conftest import CASE_ID, EXECUTION_ID, FakeService

SERVICE = settings.auth_service_id

#: Autentica-se no GEEA, mas está registado noutra unidade orgânica: entra na
#: plataforma e não chega a esta automação.
OTHER_AREA_MEMBER = Principal(
    subject="s",
    username="m004410",
    name="Auditor de teste",
    email="auditor.teste@mozabanco.co.mz",
    areas=frozenset(),
    service_access={},
    department_code="1330",
    department="Área de Auditoria Interna",
    function="Técnico",
    employee_id="4410",
)

#: Da área, e sem função de chefia. Vê e faz o mesmo que o director: é o ponto
#: todo do acesso por área.
AREA_TECHNICIAN = Principal(
    subject="s",
    username="m007000",
    name="Técnico de teste",
    email="tecnico.teste@mozabanco.co.mz",
    areas=frozenset({"channels"}),
    service_access={},
    department_code="3230",
    department="Canais e Serviços de Integração",
    function="Técnico",
    employee_id="7000",
)

READ_ROUTES = (
    ("get", "/pos/validacao-credito-fecho/execucoes/ultima"),
    ("get", f"/pos/validacao-credito-fecho/execucoes/{EXECUTION_ID}/detalhes"),
    ("get", f"/pos/validacao-credito-fecho/execucoes/{EXECUTION_ID}/relatorio"),
)


def consumer(service: str, level: AccessLevel) -> Principal:
    """Quem entra pela concessão do microserviço, e não por área nenhuma."""
    return Principal(
        subject="s",
        username="api-validacao-dsti",
        name="Validação DSTI",
        email="",
        areas=frozenset(),
        service_access={service: level},
        department_code="",
        department="",
        function="",
        employee_id="",
    )


@pytest.fixture
def anonymous(service: FakeService) -> Any:
    """A aplicação com as camadas de baixo falsas, mas a autenticação real."""
    app.dependency_overrides[get_validation_service] = lambda: service
    app.dependency_overrides[get_case_service] = lambda: service
    with TestClient(app) as http_client:
        yield http_client
    app.dependency_overrides.clear()


class TestWithoutToken:
    @pytest.mark.parametrize(("method", "path"), READ_ROUTES)
    def test_read_routes_require_session(self, anonymous, method, path):
        response = getattr(anonymous, method)(path)

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthenticated"
        # A norma manda dizer ao cliente como se autentica; é também o que diz
        # ao SPA que o caminho é renovar a sessão, e não mostrar um erro.
        assert response.headers["www-authenticate"] == "Bearer"

    def test_running_a_validation_requires_session(self, anonymous, files):
        response = anonymous.post("/pos/validacao-credito-fecho/execucoes", files=files)
        assert response.status_code == 401

    def test_invalid_token_does_not_return_500(self, anonymous):
        """Um cabeçalho inventado é um pedido inválido, não uma avaria nossa."""
        response = anonymous.get(
            "/pos/validacao-credito-fecho/execucoes/ultima",
            headers={"Authorization": "Bearer nao-e-um-jwt"},
        )
        assert response.status_code == 401

    def test_health_is_excluded(self, anonymous):
        """Quem o consulta é o Docker, e não tem sessão nenhuma."""
        assert anonymous.get("/health").status_code == 200


@pytest.fixture
def as_user(service: FakeService) -> Any:
    """Substitui-se só quem está do outro lado; a guarda corre a sério."""

    def sign_in(principal: Principal) -> TestClient:
        app.dependency_overrides[get_validation_service] = lambda: service
        app.dependency_overrides[get_case_service] = lambda: service
        app.dependency_overrides[auth.principal] = lambda: principal
        return TestClient(app)

    yield sign_in
    app.dependency_overrides.clear()


class TestByArea:
    """Quem é da área faz tudo o que a automação faz."""

    @pytest.fixture
    def outsider(self, as_user: Any) -> Any:
        """Uma sessão válida de quem não é da área: autenticado, e mais nada."""
        with as_user(OTHER_AREA_MEMBER) as http_client:
            yield http_client

    @pytest.mark.parametrize(("method", "path"), READ_ROUTES)
    def test_other_area_cannot_even_read(self, outsider, method, path):
        """A automação é do departamento a que pertence — não é do banco todo."""
        response = getattr(outsider, method)(path)

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"

    def test_other_area_cannot_run_validations(self, outsider, files):
        response = outsider.post("/pos/validacao-credito-fecho/execucoes", files=files)
        assert response.status_code == 403

    def test_other_area_cannot_resolve_cases(self, outsider):
        response = outsider.patch(
            f"/pos/validacao-credito-fecho/casos/{CASE_ID}", json={"status": "resolved"}
        )
        assert response.status_code == 403

    def test_area_member_reads(self, as_user):
        with as_user(AREA_TECHNICIAN) as http_client:
            response = http_client.get("/pos/validacao-credito-fecho/execucoes/ultima")
        assert response.status_code == 200

    def test_area_member_runs_validations(self, as_user, files):
        with as_user(AREA_TECHNICIAN) as http_client:
            response = http_client.post("/pos/validacao-credito-fecho/execucoes", files=files)
        assert response.status_code == 201

    def test_job_function_reserves_nothing(self, as_user):
        """Um técnico regulariza um caso tal como o director da área o faz."""
        with as_user(AREA_TECHNICIAN) as http_client:
            response = http_client.patch(
                f"/pos/validacao-credito-fecho/casos/{CASE_ID}", json={"status": "resolved"}
            )
        assert response.status_code == 200


class TestByServiceAccess:
    """A concessão fina: um microserviço, com leitura ou com escrita."""

    @pytest.mark.parametrize(("method", "path"), READ_ROUTES)
    def test_read_grant_reads(self, as_user, method, path):
        with as_user(consumer(SERVICE, AccessLevel.READ)) as http_client:
            response = getattr(http_client, method)(path)

        assert response.status_code == 200

    def test_read_grant_cannot_run_validations(self, as_user, files):
        with as_user(consumer(SERVICE, AccessLevel.READ)) as http_client:
            response = http_client.post("/pos/validacao-credito-fecho/execucoes", files=files)

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"

    def test_read_grant_cannot_resolve_cases(self, as_user):
        with as_user(consumer(SERVICE, AccessLevel.READ)) as http_client:
            response = http_client.patch(
                f"/pos/validacao-credito-fecho/casos/{CASE_ID}", json={"status": "resolved"}
            )

        assert response.status_code == 403

    def test_write_grant_runs_validations(self, as_user, files):
        with as_user(consumer(SERVICE, AccessLevel.WRITE)) as http_client:
            response = http_client.post("/pos/validacao-credito-fecho/execucoes", files=files)

        assert response.status_code == 201

    def test_write_grant_also_reads(self, as_user):
        with as_user(consumer(SERVICE, AccessLevel.WRITE)) as http_client:
            response = http_client.get("/pos/validacao-credito-fecho/execucoes/ultima")

        assert response.status_code == 200

    @pytest.mark.parametrize(("method", "path"), READ_ROUTES)
    def test_grant_on_another_service_opens_nothing(self, as_user, method, path):
        """É o que faz a concessão ser por microserviço, e não pela plataforma."""
        with as_user(consumer("outra-automacao", AccessLevel.WRITE)) as http_client:
            response = getattr(http_client, method)(path)

        assert response.status_code == 403
