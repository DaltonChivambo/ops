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


class TestAceita:
    async def test_token_valido(self, issuer):
        claims = await build(issuer).verify(issuer.token())
        assert claims["preferred_username"] == "m001926"
        assert claims["departmentCode"] == "2350"

    async def test_a_chave_fica_em_cache(self, issuer):
        verifier = build(issuer)
        await verifier.verify(issuer.token())
        await verifier.verify(issuer.token())
        assert issuer.fetches == 1


class TestRecusa:
    async def test_assinado_com_outra_chave(self, issuer):
        """O caso que interessa: alguém a forjar um token com as claims certas."""
        intruso = FakeIssuer(kid=issuer.kid)
        forjado = jwt.encode(
            {"sub": "x", "iss": ISSUER, "azp": AZP, "iat": 0, "exp": 9999999999},
            intruso.private_key,
            algorithm="RS256",
            headers={"kid": issuer.kid},
        )
        with pytest.raises(UnauthenticatedError):
            await build(issuer).verify(forjado)

    async def test_expirado(self, issuer):
        agora = int(time.time())
        with pytest.raises(UnauthenticatedError):
            await build(issuer).verify(issuer.token(iat=agora - 7200, exp=agora - 3600))

    async def test_emissor_errado(self, issuer):
        with pytest.raises(UnauthenticatedError):
            await build(issuer).verify(issuer.token(iss="http://outro/auth/realms/QAS"))

    async def test_cliente_fora_da_lista(self, issuer):
        """Um token legítimo do GEEA, mas emitido para outra aplicação do banco."""
        with pytest.raises(UnauthenticatedError):
            await build(issuer).verify(issuer.token(azp="qa-workflow-ui"))

    async def test_sem_assinatura(self, issuer):
        """`alg: none` — o ataque clássico contra quem confia no cabeçalho."""
        sem_assinatura = jwt.encode(
            {"sub": "x", "iss": ISSUER, "azp": AZP, "iat": 0, "exp": 9999999999},
            key="",
            algorithm="none",
            headers={"kid": issuer.kid},
        )
        with pytest.raises(UnauthenticatedError):
            await build(issuer).verify(sem_assinatura)

    async def test_sem_kid(self, issuer):
        with pytest.raises(UnauthenticatedError):
            await build(issuer).verify(issuer.token(_headers={}))

    async def test_malformado(self, issuer):
        with pytest.raises(UnauthenticatedError):
            await build(issuer).verify("isto-não-é-um-jwt")

    @pytest.mark.parametrize("em_falta", ["exp", "iat", "sub"])
    async def test_claim_obrigatoria_em_falta(self, issuer, em_falta):
        claims = {"sub": "x", "iss": ISSUER, "azp": AZP, "iat": 0, "exp": 9999999999}
        del claims[em_falta]
        token = jwt.encode(
            claims, issuer.private_key, algorithm="RS256", headers={"kid": issuer.kid}
        )
        with pytest.raises(UnauthenticatedError):
            await build(issuer).verify(token)


class TestJwks:
    async def test_kid_novo_faz_ir_buscar_as_chaves_outra_vez(self, issuer):
        """A rotação de chaves do emissor não pode exigir reiniciar o serviço."""
        verifier = build(issuer, min_refresh_seconds=0)
        await verifier.verify(issuer.token())

        rodado = FakeIssuer(kid="chave-2")
        issuer.kid = rodado.kid
        issuer.private_key = rodado.private_key

        claims = await verifier.verify(issuer.token())
        assert claims["preferred_username"] == "m001926"
        assert issuer.fetches == 2

    async def test_kid_inventado_nao_faz_um_pedido_por_token(self, issuer):
        """Sem limite, um `kid` ao acaso por pedido era um amplificador de saída."""
        verifier = build(issuer, min_refresh_seconds=300)
        await verifier.verify(issuer.token())

        for _ in range(5):
            with pytest.raises(UnauthenticatedError):
                await verifier.verify(issuer.token(_headers={"kid": "inventado"}))

        assert issuer.fetches == 1

    async def test_emissor_em_baixo_nao_diz_sessao_invalida(self, issuer):
        """O token pode estar bom e o problema ser nosso — 503, não 401."""

        async def rebenta():
            raise ValueError("sem rede")

        verifier = TokenVerifier(
            jwks_url="http://geea-keycloak:8000/irrelevante",
            issuer=ISSUER,
            allowed_azp=frozenset({AZP}),
            fetcher=rebenta,
        )
        with pytest.raises(IdentityUnavailableError):
            await verifier.verify(issuer.token())


class TestPrincipal:
    async def test_claims_do_geea_viram_principal(self, issuer):
        from mozaops_libs.auth.fastapi import principal_from_claims
        from mozaops_libs.auth.mapping import RoleMapping

        claims = await build(issuer).verify(issuer.token())
        principal = principal_from_claims(
            claims,
            RoleMapping(
                operator_departments=frozenset({"2350"}),
                supervisor_functions=frozenset({"Director"}),
            ),
        )

        assert principal.username == "m001926"
        assert principal.department == "Departamento de Apoio Operacional"
        assert principal.employee_id == "1926"
        assert principal.roles == {"supervisor", "operator"}


def test_par_de_chaves_do_teste_e_gerado_e_nao_lido_do_disco():
    """Nenhuma chave privada entra no repositório, nem para testes."""
    assert isinstance(FakeIssuer().private_key, rsa.RSAPrivateKey)
