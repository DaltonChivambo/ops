"""A concessão por microserviço: quem pode o quê, sem passar pela área."""

import pytest

from mozaops_libs.auth.access import AccessLevel, parse_service_access
from mozaops_libs.auth.principal import Principal

SERVICE = "pos-closing-credit-validation"


def principal(**overrides: object) -> Principal:
    base: dict[str, object] = {
        "subject": "s",
        "username": "api-validacao-dsti",
        "name": "Validação DSTI",
        "email": "",
        "areas": frozenset(),
        "service_access": {},
        "department_code": "",
        "department": "",
        "function": "",
        "employee_id": "",
    }
    return Principal(**{**base, **overrides})  # type: ignore[arg-type]


class TestRequiredLevel:
    @pytest.mark.parametrize("method", ["GET", "HEAD", "OPTIONS", "get"])
    def test_safe_methods_need_only_read(self, method):
        assert AccessLevel.required_for(method) is AccessLevel.READ

    @pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE", "patch"])
    def test_everything_else_needs_write(self, method):
        """Uma rota que mute nasce a exigir escrita, sem ninguém a marcar."""
        assert AccessLevel.required_for(method) is AccessLevel.WRITE

    def test_write_covers_read(self):
        assert AccessLevel.WRITE >= AccessLevel.READ


class TestParseServiceAccess:
    def test_reads_the_role_format(self):
        granted = parse_service_access([f"service:{SERVICE}:read", "service:outra:write"])

        assert granted == {SERVICE: AccessLevel.READ, "outra": AccessLevel.WRITE}

    def test_highest_level_wins(self):
        granted = parse_service_access([f"service:{SERVICE}:read", f"service:{SERVICE}:write"])

        assert granted[SERVICE] is AccessLevel.WRITE

    def test_areas_are_not_service_grants(self):
        assert parse_service_access(["channels", "all-areas"]) == {}

    @pytest.mark.parametrize(
        "role",
        [
            f"service:{SERVICE}",
            f"service:{SERVICE}:",
            f"service:{SERVICE}:admin",
            "service:",
            "service::read",
            f"svc:{SERVICE}:read",
        ],
    )
    def test_malformed_roles_open_nothing(self, role):
        """Quem atribui no realm não conhece as convenções: erro tem de fechar."""
        assert parse_service_access([role]) == {}


class TestIsAllowed:
    def test_read_grant_allows_reading(self):
        who = principal(service_access={SERVICE: AccessLevel.READ})

        assert who.is_allowed(SERVICE, "channels", AccessLevel.READ)

    def test_read_grant_refuses_writing(self):
        who = principal(service_access={SERVICE: AccessLevel.READ})

        assert not who.is_allowed(SERVICE, "channels", AccessLevel.WRITE)

    def test_write_grant_allows_both(self):
        who = principal(service_access={SERVICE: AccessLevel.WRITE})

        assert who.is_allowed(SERVICE, "channels", AccessLevel.READ)
        assert who.is_allowed(SERVICE, "channels", AccessLevel.WRITE)

    def test_grant_on_another_service_opens_nothing_here(self):
        """É o que faz a concessão ser por microserviço e não pela plataforma."""
        who = principal(service_access={"outra-automacao": AccessLevel.WRITE})

        assert not who.is_allowed(SERVICE, "channels", AccessLevel.READ)

    def test_area_still_allows_everything(self):
        """Quem entra pela área não perde nada com isto."""
        who = principal(areas=frozenset({"channels"}))

        assert who.is_allowed(SERVICE, "channels", AccessLevel.WRITE)

    def test_all_areas_still_allows_everything(self):
        who = principal(areas=frozenset({"all-areas"}))

        assert who.is_allowed(SERVICE, "channels", AccessLevel.WRITE)

    def test_all_areas_is_not_a_service_grant(self):
        """Abre áreas; não é um atalho para abrir serviços de outras áreas."""
        who = principal(areas=frozenset({"all-areas"}))

        assert who.access_to(SERVICE) is None

    def test_nothing_granted_opens_nothing(self):
        assert not principal().is_allowed(SERVICE, "channels", AccessLevel.READ)
