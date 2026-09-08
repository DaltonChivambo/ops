"""O mapa de áreas — a decisão de quem entra onde, testada sem rede."""

import pytest

from mozaops_libs.auth.areas import AreaMapping, map_areas, parse_area_map, parse_set

MAPPING = AreaMapping(
    by_unit={"payments-and-channels": frozenset({"2350", "2442"})},
    by_user={"payments-and-channels": frozenset({"m004410"})},
)


def claims(**overrides: object) -> dict:
    base = {
        "preferred_username": "m009999",
        "departmentCode": "1600",
        "function": "Técnico",
        "realm_access": {"roles": ["work_queue", "manage_employee"]},
    }
    return {**base, **overrides}


class TestPorUnidade:
    def test_a_unidade_do_dop_abre_a_area(self):
        assert map_areas(claims(departmentCode="2350"), MAPPING) == {"payments-and-channels"}

    def test_outra_unidade_da_mesma_area_tambem_abre(self):
        """Uma área do MozaOps corresponde a mais do que uma unidade do GEEA."""
        assert map_areas(claims(departmentCode="2442"), MAPPING) == {"payments-and-channels"}

    def test_a_funcao_nao_conta(self):
        """Director, chefe ou técnico: dentro da área fazem o mesmo."""
        tecnico = map_areas(claims(departmentCode="2350", function="Técnico"), MAPPING)
        director = map_areas(claims(departmentCode="2350", function="Director"), MAPPING)

        assert tecnico == director == {"payments-and-channels"}

    def test_os_papeis_do_geea_nao_contam(self):
        """`manage_employee` é do sistema deles, e não abre nada aqui."""
        given = claims(realm_access={"roles": ["manage_employee", "mozaops_supervisor"]})
        assert map_areas(given, MAPPING) == frozenset()


class TestPorUtilizador:
    def test_lista_explicita_abre_a_area(self):
        """Quem está registado noutra unidade mas trabalha nesta."""
        assert map_areas(claims(preferred_username="m004410"), MAPPING) == {"payments-and-channels"}

    def test_soma_se_a_unidade_em_vez_de_a_substituir(self):
        given = claims(preferred_username="m004410", departmentCode="2350")
        assert map_areas(given, MAPPING) == {"payments-and-channels"}


class TestSemCorrespondencia:
    def test_ninguem_entra_por_omissao(self):
        """O ponto todo: autenticar não é ser autorizado."""
        assert map_areas(claims(), MAPPING) == frozenset()

    @pytest.mark.parametrize("valor", [None, "", "   "])
    def test_unidade_em_branco_nao_corresponde(self, valor):
        assert map_areas(claims(departmentCode=valor), MAPPING) == frozenset()

    def test_claims_vazias_nao_rebentam(self):
        assert map_areas({}, MAPPING) == frozenset()

    def test_utilizador_em_branco_nao_corresponde_a_entrada_vazia(self):
        """Uma entrada vazia na lista corresponderia a um `username` vazio."""
        mapping = AreaMapping(by_user={"pos": parse_set(",,")})
        assert map_areas({"preferred_username": ""}, mapping) == frozenset()


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


class TestParseAreaMap:
    def test_le_a_forma_da_variavel_de_ambiente(self):
        assert parse_area_map("payments-and-channels:2350,2442;cartoes:2360") == {
            "payments-and-channels": frozenset({"2350", "2442"}),
            "cartoes": frozenset({"2360"}),
        }

    def test_tolera_espacos_e_pontos_e_virgula_a_mais(self):
        assert parse_area_map(" pos : 2350 , 2442 ;; ") == {"pos": frozenset({"2350", "2442"})}

    def test_a_mesma_area_duas_vezes_soma(self):
        assert parse_area_map("pos:2350;pos:2442") == {"pos": frozenset({"2350", "2442"})}

    @pytest.mark.parametrize("raw", ["", None, "sem-dois-pontos", ":2350", "pos:", "pos: , "])
    def test_o_que_nao_tem_forma_nao_rebenta_nem_abre_nada(self, raw):
        """Rebentar aqui deixava o serviço sem arrancar por causa de uma vírgula."""
        assert parse_area_map(raw) == {}
