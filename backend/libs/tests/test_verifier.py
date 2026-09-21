"""A validação de tokens: o que se aceita, e sobretudo o que se recusa."""

import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from mozaops_libs.auth.errors import IdentityUnavailableError, UnauthenticatedError
from mozaops_libs.auth.verifier import TokenVerifier
from tests.conftest import AZP, ISSUER, FakeIssuer


def build(issuer: FakeIssuer, **kwargs) -> TokenVerifier:
    return TokenVerifier(
        jwks_url="http://geea-keycloak:8000/irrelevante",
        issuer=ISSUER,
        allowed_azp=frozenset({AZP}),
        fetcher=issuer.fetch,
        **kwargs,
    )


class TestAccepts:
    async def test_valid_token(self, issuer):
        claims = await build(issuer).verify(issuer.token())
        assert claims["preferred_username"] == "m001926"
        assert claims["departmentCode"] == "2350"

    async def test_key_is_cached(self, issuer):
        verifier = build(issuer)
        await verifier.verify(issuer.token())
        await verifier.verify(issuer.token())
        assert issuer.fetches == 1


class TestRejects:
    async def test_signed_with_another_key(self, issuer):
        """O caso que interessa: alguém a forjar um token com as claims certas."""
        intruder = FakeIssuer(kid=issuer.kid)
        forged = jwt.encode(
            {"sub": "x", "iss": ISSUER, "azp": AZP, "iat": 0, "exp": 9999999999},
            intruder.private_key,
            algorithm="RS256",
            headers={"kid": issuer.kid},
        )
        with pytest.raises(UnauthenticatedError):
            await build(issuer).verify(forged)

    async def test_expired(self, issuer):
        now = int(time.time())
        with pytest.raises(UnauthenticatedError):
            await build(issuer).verify(issuer.token(iat=now - 7200, exp=now - 3600))

    async def test_wrong_issuer(self, issuer):
        with pytest.raises(UnauthenticatedError):
            await build(issuer).verify(issuer.token(iss="http://outro/auth/realms/QAS"))

    async def test_client_not_in_allowed_list(self, issuer):
        """Um token legítimo do GEEA, mas emitido para outra aplicação do banco."""
        with pytest.raises(UnauthenticatedError):
            await build(issuer).verify(issuer.token(azp="qa-workflow-ui"))

    async def test_unsigned(self, issuer):
        """`alg: none` — o ataque clássico contra quem confia no cabeçalho."""
        unsigned = jwt.encode(
            {"sub": "x", "iss": ISSUER, "azp": AZP, "iat": 0, "exp": 9999999999},
            key="",
            algorithm="none",
            headers={"kid": issuer.kid},
        )
        with pytest.raises(UnauthenticatedError):
            await build(issuer).verify(unsigned)

    async def test_missing_kid(self, issuer):
        with pytest.raises(UnauthenticatedError):
            await build(issuer).verify(issuer.token(_headers={}))

    async def test_malformed(self, issuer):
        with pytest.raises(UnauthenticatedError):
            await build(issuer).verify("isto-não-é-um-jwt")

    @pytest.mark.parametrize("missing", ["exp", "iat", "sub"])
    async def test_missing_required_claim(self, issuer, missing):
        claims = {"sub": "x", "iss": ISSUER, "azp": AZP, "iat": 0, "exp": 9999999999}
        del claims[missing]
        token = jwt.encode(
            claims, issuer.private_key, algorithm="RS256", headers={"kid": issuer.kid}
        )
        with pytest.raises(UnauthenticatedError):
            await build(issuer).verify(token)


class TestJwks:
    async def test_new_kid_refetches_keys(self, issuer):
        """A rotação de chaves do emissor não pode exigir reiniciar o serviço."""
        verifier = build(issuer, min_refresh_seconds=0)
        await verifier.verify(issuer.token())

        rotated = FakeIssuer(kid="chave-2")
        issuer.kid = rotated.kid
        issuer.private_key = rotated.private_key

        claims = await verifier.verify(issuer.token())
        assert claims["preferred_username"] == "m001926"
        assert issuer.fetches == 2

    async def test_unknown_kid_does_not_fetch_per_token(self, issuer):
        """Sem limite, um `kid` ao acaso por pedido era um amplificador de saída."""
        verifier = build(issuer, min_refresh_seconds=300)
        await verifier.verify(issuer.token())

        for _ in range(5):
            with pytest.raises(UnauthenticatedError):
                await verifier.verify(issuer.token(_headers={"kid": "inventado"}))

        assert issuer.fetches == 1

    async def test_issuer_down_is_not_reported_as_invalid_session(self, issuer):
        """O token pode estar bom e o problema ser nosso — 503, não 401."""

        async def failing_fetch():
            raise ValueError("sem rede")

        verifier = TokenVerifier(
            jwks_url="http://geea-keycloak:8000/irrelevante",
            issuer=ISSUER,
            allowed_azp=frozenset({AZP}),
            fetcher=failing_fetch,
        )
        with pytest.raises(IdentityUnavailableError):
            await verifier.verify(issuer.token())


class TestPrincipal:
    async def test_geea_claims_become_principal(self, issuer):
        from mozaops_libs.auth.areas import AreaMapping
        from mozaops_libs.auth.fastapi import principal_from_claims

        claims = await build(issuer).verify(issuer.token())
        principal = principal_from_claims(
            claims,
            AreaMapping(by_unit={"payments-and-channels": frozenset({"2350"})}),
        )

        assert principal.username == "m001926"
        assert principal.department == "Departamento de Apoio Operacional"
        assert principal.employee_id == "1926"
        assert principal.areas == {"payments-and-channels"}

    async def test_all_areas_role_opens_everything(self, issuer):
        from mozaops_libs.auth import ALL_AREAS
        from mozaops_libs.auth.areas import AreaMapping
        from mozaops_libs.auth.fastapi import principal_from_claims

        token = issuer.token(resource_access={AZP: {"roles": [ALL_AREAS]}})
        principal = principal_from_claims(await build(issuer).verify(token), AreaMapping())

        assert principal.has_area("channels")
        assert principal.has_area("uma-area-que-ainda-nao-existe")

    async def test_without_the_area_nothing_opens(self, issuer):
        from mozaops_libs.auth.areas import AreaMapping
        from mozaops_libs.auth.fastapi import principal_from_claims

        token = issuer.token(resource_access={AZP: {"roles": ["channels"]}})
        principal = principal_from_claims(await build(issuer).verify(token), AreaMapping())

        assert principal.has_area("channels")
        assert not principal.has_area("fraud-monitoring")


class TestDisplayName:
    """O nome como se mostra — a regra está em `fastapi.display_name`."""

    def test_repeated_surname_is_collapsed(self):
        from mozaops_libs.auth.fastapi import display_name

        assert display_name({"name": "Dalton Chivambo Chivambo"}) == "Dalton Chivambo"

    def test_full_name_is_kept(self):
        from mozaops_libs.auth.fastapi import display_name

        assert display_name({"name": "John Doe"}) == "John Doe"

    def test_falls_back_when_the_directory_has_no_name(self):
        from mozaops_libs.auth.fastapi import display_name

        assert display_name({"given_name": "Ana", "preferred_username": "m004410"}) == "Ana"
        assert display_name({"preferred_username": "m004410"}) == "m004410"
        assert display_name({}) == ""


def test_test_key_pair_is_generated_not_read_from_disk():
    """Nenhuma chave privada entra no repositório, nem para testes."""
    assert isinstance(FakeIssuer().private_key, rsa.RSAPrivateKey)
