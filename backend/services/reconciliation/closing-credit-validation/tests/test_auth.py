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

#: Autentica-se no GEEA, mas está registado noutra unidade orgânica: entra na
#: plataforma e não chega a esta automação.
DE_OUTRA_AREA = Principal(
    subject="s",
    username="m004410",
    name="Auditor de teste",
    email="auditor.teste@mozabanco.co.mz",
    areas=frozenset(),
    department_code="1330",
    department="Área de Auditoria Interna",
    function="Técnico",
    employee_id="4410",
)

#: Da área, e sem função de chefia. Vê e faz o mesmo que o director: é o ponto
#: todo do acesso por área.
TECNICO_DA_AREA = Principal(
    subject="s",
    username="m007000",
    name="Técnico de teste",
    email="tecnico.teste@mozabanco.co.mz",
    areas=frozenset({"payments-and-channels"}),
    department_code="2350",
    department="Departamento de Apoio Operacional",
    function="Técnico",
    employee_id="7000",
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


class TestPorArea:
    """Substitui-se só quem está do outro lado; a guarda corre a sério."""

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
    def de_fora(self, como: Any) -> Any:
        """Uma sessão válida de quem não é da área: autenticado, e mais nada."""
        with como(DE_OUTRA_AREA) as cliente:
            yield cliente

    @pytest.mark.parametrize(("metodo", "caminho"), ROTAS_DE_LEITURA)
    def test_de_outra_area_nem_le(self, de_fora, metodo, caminho):
        """A automação é do departamento a que pertence — não é do banco todo."""
        response = getattr(de_fora, metodo)(caminho)

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"

    def test_de_outra_area_nao_corre_validacoes(self, de_fora, ficheiros):
        response = de_fora.post("/pos/validacao-credito-fecho/execucoes", files=ficheiros)
        assert response.status_code == 403

    def test_de_outra_area_nao_regulariza_casos(self, de_fora):
        response = de_fora.patch(
            f"/pos/validacao-credito-fecho/casos/{CASE_ID}", json={"status": "resolved"}
        )
        assert response.status_code == 403

    def test_da_area_le(self, como):
        with como(TECNICO_DA_AREA) as cliente:
            response = cliente.get("/pos/validacao-credito-fecho/execucoes/ultima")
        assert response.status_code == 200

    def test_da_area_corre_validacoes(self, como, ficheiros):
        with como(TECNICO_DA_AREA) as cliente:
            response = cliente.post("/pos/validacao-credito-fecho/execucoes", files=ficheiros)
        assert response.status_code == 201

    def test_a_funcao_nao_reserva_nada(self, como):
        """Um técnico regulariza um caso tal como o director da área o faz."""
        with como(TECNICO_DA_AREA) as cliente:
            response = cliente.patch(
                f"/pos/validacao-credito-fecho/casos/{CASE_ID}", json={"status": "resolved"}
            )
        assert response.status_code == 200
