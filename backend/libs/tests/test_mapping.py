"""O mapa de papéis — a decisão de quem pode o quê, testada sem rede."""

import pytest

from mozaops_libs.auth.mapping import RoleMapping, map_roles, parse_set

MAPPING = RoleMapping(
    supervisor_users=frozenset({"m001926"}),
    auditor_users=frozenset({"m004410"}),
    operator_users=frozenset({"m007000"}),
    operator_departments=frozenset({"2350"}),
    supervisor_functions=frozenset({"Director", "Chefe"}),
)


def claims(**overrides: object) -> dict:
    base = {
        "preferred_username": "m009999",
        "departmentCode": "1600",
        "function": "Técnico",
        "realm_access": {"roles": ["work_queue", "manage_employee"]},
    }
    return {**base, **overrides}


class TestPorDepartamento:
    def test_departamento_do_dop_da_operador(self):
        assert map_roles(claims(departmentCode="2350"), MAPPING) == {"operator"}

    def test_funcao_de_chefia_no_departamento_certo_da_supervisor(self):
        assert map_roles(claims(departmentCode="2350", function="Director"), MAPPING) == {
            "supervisor",
            "operator",
        }

    def test_funcao_de_chefia_noutro_departamento_nao_da_nada(self):
        """Ser director não é ser director *disto*."""
        assert map_roles(claims(departmentCode="1600", function="Director"), MAPPING) == frozenset()


class TestPorUtilizador:
    def test_lista_explicita_de_supervisores(self):
        assert map_roles(claims(preferred_username="m001926"), MAPPING) == {
            "supervisor",
            "operator",
        }

    def test_auditor_nao_ganha_operador(self):
        """Auditar é ver; não dá escrita nenhuma."""
        assert map_roles(claims(preferred_username="m004410"), MAPPING) == {"auditor"}

    def test_utilizador_ganha_ao_departamento(self):
        """Estar na lista é mais forte do que a regra genérica do departamento."""
        assert map_roles(claims(preferred_username="m004410", departmentCode="2350"), MAPPING) == {
            "auditor"
        }


class TestPapeisVindosDoGeea:
    def test_prefixo_acordado_ganha_a_tudo(self):
        """No dia em que o banco criar os papéis, a nossa tabela deixa de contar."""
        given = claims(
            preferred_username="m004410",  # auditor na nossa lista
            realm_access={"roles": ["work_queue", "mozaops_supervisor"]},
        )
        assert map_roles(given, MAPPING) == {"supervisor", "operator"}

    def test_papel_desconhecido_com_o_prefixo_e_ignorado(self):
        given = claims(realm_access={"roles": ["mozaops_administrador"]})
        assert map_roles(given, MAPPING) == frozenset()

    def test_papeis_do_geea_sem_o_prefixo_nao_contam(self):
        """`manage_employee` é do sistema deles, não nosso."""
        given = claims(realm_access={"roles": ["manage_employee", "supervisor"]})
        assert map_roles(given, MAPPING) == frozenset()


class TestSemCorrespondencia:
    def test_ninguem_e_operador_por_omissao(self):
        """O ponto todo: autenticar não é ser autorizado."""
        assert map_roles(claims(), MAPPING) == frozenset()

    @pytest.mark.parametrize("valor", [None, "", "   "])
    def test_departamento_em_branco_nao_corresponde(self, valor):
        assert map_roles(claims(departmentCode=valor), MAPPING) == frozenset()

    def test_claims_vazias_nao_rebentam(self):
        assert map_roles({}, MAPPING) == frozenset()


class TestParseSet:
    @pytest.mark.parametrize(
        ("raw", "esperado"),
        [
            ("a,b,c", {"a", "b", "c"}),
            (" a , b ,, c ", {"a", "b", "c"}),
            ("", frozenset()),
            (None, frozenset()),
            (",,,", frozenset()),
        ],
    )
    def test_normaliza_listas_de_variaveis_de_ambiente(self, raw, esperado):
        assert parse_set(raw) == esperado

    def test_lista_vazia_nao_cria_utilizador_em_branco(self):
        """Uma entrada vazia corresponderia a um `username` vazio, e deixava entrar."""
        mapping = RoleMapping(supervisor_users=parse_set(",,"))
        assert map_roles({"preferred_username": ""}, mapping) == frozenset()
