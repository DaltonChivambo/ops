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
from mozaops_libs.auth import Principal
from tests.conftest import CASE_ID, EXECUTION_ID, FakeService

AUDITOR = Principal(
    subject="s",
    username="m004410",
    name="Auditor de teste",
    email="auditor.teste@mozabanco.co.mz",
    roles=frozenset({"auditor"}),
    department_code="1330",
    department="Área de Auditoria Interna",
    function="Técnico",
    employee_id="4410",
)

ROTAS_DE_LEITURA = (
    ("get", "/pos/validacao-credito-fecho/execucoes/ultima"),
    ("get", f"/pos/validacao-credito-fecho/execucoes/{EXECUTION_ID}/detalhes"),
    ("get", f"/pos/validacao-credito-fecho/execucoes/{EXECUTION_ID}/relatorio"),
)


@pytest.fixture
def sem_sessao(service: FakeService) -> Any:
    """A aplicação com as camadas de baixo falsas, mas a autenticação real."""
    app.dependency_overrides[get_validation_service] = lambda: service
    app.dependency_overrides[get_case_service] = lambda: service
    with TestClient(app) as cliente:
        yield cliente
    app.dependency_overrides.clear()


class TestSemToken:
    @pytest.mark.parametrize(("metodo", "caminho"), ROTAS_DE_LEITURA)
    def test_rotas_de_leitura_pedem_sessao(self, sem_sessao, metodo, caminho):
        response = getattr(sem_sessao, metodo)(caminho)

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthenticated"
        # A norma manda dizer ao cliente como se autentica; é também o que diz
        # ao SPA que o caminho é renovar a sessão, e não mostrar um erro.
        assert response.headers["www-authenticate"] == "Bearer"

    def test_correr_uma_validacao_pede_sessao(self, sem_sessao, ficheiros):
        response = sem_sessao.post("/pos/validacao-credito-fecho/execucoes", files=ficheiros)
        assert response.status_code == 401

    def test_token_invalido_nao_da_500(self, sem_sessao):
        """Um cabeçalho inventado é um pedido inválido, não uma avaria nossa."""
        response = sem_sessao.get(
            "/pos/validacao-credito-fecho/execucoes/ultima",
            headers={"Authorization": "Bearer nao-e-um-jwt"},
        )
        assert response.status_code == 401

    def test_o_health_fica_de_fora(self, sem_sessao):
        """Quem o consulta é o Docker, e não tem sessão nenhuma."""
        assert sem_sessao.get("/health").status_code == 200


OPERADOR = Principal(
    subject="s",
    username="m007000",
    name="Operador de teste",
    email="operador.teste@mozabanco.co.mz",
    roles=frozenset({"operator"}),
    department_code="2350",
    department="Departamento de Apoio Operacional",
    function="Técnico",
    employee_id="7000",
)


class TestPapeis:
    """Substitui-se só quem está do outro lado; as guardas correm a sério."""

    @pytest.fixture
    def como(self, service: FakeService) -> Any:
        def entrar(principal: Principal) -> TestClient:
            app.dependency_overrides[get_validation_service] = lambda: service
            app.dependency_overrides[get_case_service] = lambda: service
            app.dependency_overrides[auth.principal] = lambda: principal
            return TestClient(app)

        yield entrar
        app.dependency_overrides.clear()

    @pytest.fixture
    def auditor(self, como: Any) -> Any:
        """Uma sessão de auditor: entra e vê, mas não mexe."""
        with como(AUDITOR) as cliente:
            yield cliente

    def test_auditor_le(self, auditor):
        assert auditor.get("/pos/validacao-credito-fecho/execucoes/ultima").status_code == 200

    def test_auditor_nao_corre_validacoes(self, auditor, ficheiros):
        response = auditor.post("/pos/validacao-credito-fecho/execucoes", files=ficheiros)

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"

    def test_auditor_nao_regulariza_casos(self, auditor):
        """O acto com significado financeiro é de supervisor, e só dele."""
        response = auditor.patch(
            f"/pos/validacao-credito-fecho/casos/{CASE_ID}", json={"status": "resolved"}
        )
        assert response.status_code == 403

    def test_operador_corre_validacoes(self, como, ficheiros):
        with como(OPERADOR) as cliente:
            response = cliente.post("/pos/validacao-credito-fecho/execucoes", files=ficheiros)
        assert response.status_code == 201

    def test_operador_nao_regulariza_casos(self, como):
        """O SPA já esconde o botão; esconder não é controlo."""
        with como(OPERADOR) as cliente:
            response = cliente.patch(
                f"/pos/validacao-credito-fecho/casos/{CASE_ID}", json={"status": "resolved"}
            )
        assert response.status_code == 403

    def test_supervisor_regulariza(self, client):
        """O `client` do conftest é supervisor — o caminho feliz, para contraste."""
        response = client.patch(
            f"/pos/validacao-credito-fecho/casos/{CASE_ID}", json={"status": "resolved"}
        )
        assert response.status_code == 200
