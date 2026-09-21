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


class TestByUnit:
    def test_dop_unit_opens_the_area(self):
        assert map_areas(claims(departmentCode="2350"), MAPPING) == {"payments-and-channels"}

    def test_another_unit_of_same_area_also_opens(self):
        """Uma área do MozaOps corresponde a mais do que uma unidade do GEEA."""
        assert map_areas(claims(departmentCode="2442"), MAPPING) == {"payments-and-channels"}

    def test_job_function_does_not_count(self):
        """Director, chefe ou técnico: dentro da área fazem o mesmo."""
        technician = map_areas(claims(departmentCode="2350", function="Técnico"), MAPPING)
        director = map_areas(claims(departmentCode="2350", function="Director"), MAPPING)

        assert technician == director == {"payments-and-channels"}

    def test_geea_realm_roles_do_not_count(self):
        """Os papéis do realm são do sistema deles, mesmo com nome de área.

        Só contam os do nosso cliente, em `resource_access` — ver
        `TestByClientRoles`.
        """
        given = claims(realm_access={"roles": ["manage_employee", "payments-and-channels"]})
        assert map_areas(given, MAPPING) == frozenset()


class TestByClientRoles:
    def test_role_of_our_client_opens_the_area(self):
        """O realm QAS é quem provisiona: o nome do papel é o id da área."""
        given = claims(
            azp="qa-mozaops",
            resource_access={
                "qa-mozaops": {"roles": ["payments-and-channels", "fraud-monitoring"]},
                "account": {"roles": ["view-profile"]},
            },
        )
        assert map_areas(given, MAPPING) == {"payments-and-channels", "fraud-monitoring"}

    def test_roles_of_another_client_do_not_count(self):
        """Os acessos que alguém tem noutra aplicação do banco não são nossos."""
        given = claims(
            azp="qa-mozaops",
            resource_access={"qa-workflow-ui": {"roles": ["payments-and-channels"]}},
        )
        assert map_areas(given, MAPPING) == frozenset()

    def test_roles_add_to_the_unit(self):
        given = claims(
            azp="qa-mozaops",
            departmentCode="2350",
            resource_access={"qa-mozaops": {"roles": ["cartoes"]}},
        )
        assert map_areas(given, MAPPING) == {"payments-and-channels", "cartoes"}

    @pytest.mark.parametrize(
        "resource_access",
        [
            None,
            {},
            "não é um objecto",
            {"qa-mozaops": {}},
            {"qa-mozaops": {"roles": "payments-and-channels"}},
            {"qa-mozaops": {"roles": [None, 7]}},
        ],
    )
    def test_malformed_resource_access_opens_nothing(self, resource_access):
        given = claims(azp="qa-mozaops", resource_access=resource_access)
        assert map_areas(given, MAPPING) == frozenset()

    def test_without_azp_there_is_no_client_to_read(self):
        given = claims(resource_access={"qa-mozaops": {"roles": ["payments-and-channels"]}})
        assert map_areas(given, MAPPING) == frozenset()


class TestByUser:
    def test_explicit_list_opens_the_area(self):
        """Quem está registado noutra unidade mas trabalha nesta."""
        assert map_areas(claims(preferred_username="m004410"), MAPPING) == {"payments-and-channels"}

    def test_unit_is_added_not_replaced(self):
        given = claims(preferred_username="m004410", departmentCode="2350")
        assert map_areas(given, MAPPING) == {"payments-and-channels"}


class TestNoMatch:
    def test_nobody_gets_in_by_default(self):
        """O ponto todo: autenticar não é ser autorizado."""
        assert map_areas(claims(), MAPPING) == frozenset()

    @pytest.mark.parametrize("value", [None, "", "   "])
    def test_blank_unit_does_not_match(self, value):
        assert map_areas(claims(departmentCode=value), MAPPING) == frozenset()

    def test_empty_claims_do_not_break(self):
        assert map_areas({}, MAPPING) == frozenset()

    def test_blank_user_does_not_match_empty_entry(self):
        """Uma entrada vazia na lista corresponderia a um `username` vazio."""
        mapping = AreaMapping(by_user={"pos": parse_set(",,")})
        assert map_areas({"preferred_username": ""}, mapping) == frozenset()


class TestParseSet:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("a,b,c", {"a", "b", "c"}),
            (" a , b ,, c ", {"a", "b", "c"}),
            ("", frozenset()),
            (None, frozenset()),
            (",,,", frozenset()),
        ],
    )
    def test_normalizes_env_variable_lists(self, raw, expected):
        assert parse_set(raw) == expected


class TestParseAreaMap:
    def test_reads_the_env_variable_format(self):
        assert parse_area_map("payments-and-channels:2350,2442;cartoes:2360") == {
            "payments-and-channels": frozenset({"2350", "2442"}),
            "cartoes": frozenset({"2360"}),
        }

    def test_tolerates_extra_spaces_and_semicolons(self):
        assert parse_area_map(" pos : 2350 , 2442 ;; ") == {"pos": frozenset({"2350", "2442"})}

    def test_same_area_twice_adds_up(self):
        assert parse_area_map("pos:2350;pos:2442") == {"pos": frozenset({"2350", "2442"})}

    @pytest.mark.parametrize("raw", ["", None, "sem-dois-pontos", ":2350", "pos:", "pos: , "])
    def test_malformed_input_does_not_break_or_open_anything(self, raw):
        """Rebentar aqui deixava o serviço sem arrancar por causa de uma vírgula."""
        assert parse_area_map(raw) == {}
