"""Um GEEA de mentira, e a aplicação ligada a ele.

O `SSOLogin` é substituído por um duplo; o verificador de tokens continua a ser
o verdadeiro, alimentado por um JWKS de teste. Assim o que se testa é o
caminho real — o serviço não confia no que o GEEA diz, valida a assinatura —
sem depender de rede nenhuma.
"""

import json
import os
import time
from typing import Any

import jwt
import pytest

# Antes de qualquer import de `app.*`: as settings são lidas na importação.
#
# Em produção o browser vê `/api/identity/...` — o `/api` é cortado pelo
# Traefik antes de o pedido chegar aqui — e é esse o caminho do cookie. O
# cliente de teste fala com o serviço sem proxy à frente, e vê `/identity/...`,
# por isso um cookie limitado a `/api/identity` nunca lhe seria devolvido. O
# caminho por omissão é verificado à parte, em `test_sessions.py`.
os.environ.setdefault("SESSION_COOKIE_PATH", "/")
os.environ.setdefault("SESSION_COOKIE_SECURE", "false")
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from mozaops_libs.auth import AreaMapping, TokenVerifier

ISSUER = "http://geea-teste/auth/realms/QAS"
AZP = "mozaops-web"
KID = "chave-de-teste"

_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def jwks() -> dict[str, Any]:
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(_private_key.public_key()))
    jwk.pop("key_ops", None)
    return {"keys": [{**jwk, "kid": KID, "use": "sig", "alg": "RS256"}]}


def make_token(**overrides: Any) -> str:
    now = int(time.time())
    claims: dict[str, Any] = {
        "sub": "6961d9f6-5529-457b-93cb-db82230a00cb",
        "iss": ISSUER,
        "aud": "account",
        "azp": AZP,
        "iat": now,
        "exp": now + 3600,
        "preferred_username": "m001926",
        "name": "Dalton Chivambo",
        "email": "dalton.chivambo@mozabanco.co.mz",
        "departmentCode": "2350",
        "department": "Departamento de Apoio Operacional",
        "function": "Director",
        "Employee ID": "1926",
        "realm_access": {"roles": ["work_queue"]},
    }
    claims.update(overrides)
    return jwt.encode(claims, _private_key, algorithm="RS256", headers={"kid": KID})


class FakeGeea:
    """Substitui o `GeeaClient`. Regista o que recebeu, para se poder afirmar
    que a password nunca foi parar a sítio nenhum indevido."""

    def __init__(self) -> None:
        self.logins: list[tuple[str, str, str]] = []
        self.refreshes: list[str] = []
        self.valid = {"m001926": "senha-certa"}
        self.raises: Exception | None = None

    async def login(self, username: str, password: str, client_ip: str) -> dict[str, Any]:
        self.logins.append((username, password, client_ip))
        if self.raises:
            raise self.raises
        if self.valid.get(username) != password:
            from app.domain.errors import InvalidCredentialsError

            raise InvalidCredentialsError
        return self._output(make_token(preferred_username=username))

    async def refresh(self, refresh_token: str) -> dict[str, Any]:
        self.refreshes.append(refresh_token)
        if self.raises:
            raise self.raises
        if refresh_token != "refresh-valido":
            from app.domain.errors import InvalidCredentialsError

            raise InvalidCredentialsError
        return self._output(make_token())

    def _output(self, access_token: str) -> dict[str, Any]:
        return {
            "accessToken": access_token,
            "refreshToken": "refresh-valido",
            "expiresIn": "18000",
            "refreshExpiresIn": "18000",
            "tokenType": "bearer",
            "error": None,
        }


@pytest.fixture
def geea() -> FakeGeea:
    return FakeGeea()


@pytest.fixture
def mapping() -> AreaMapping:
    return AreaMapping(
        by_unit={"payments-and-channels": frozenset({"2350"})},
        by_user={"payments-and-channels": frozenset({"m004410"})},
    )


@pytest.fixture
def client(geea: FakeGeea, mapping: AreaMapping) -> TestClient:
    from app.controllers.dependencies import get_session_service
    from app.main import app
    from app.services.session_service import AttemptLimiter, SessionService

    async def fetch_jwks() -> dict[str, Any]:
        return jwks()

    verifier = TokenVerifier(
        jwks_url="http://irrelevante",
        issuer=ISSUER,
        allowed_azp=frozenset({AZP}),
        fetcher=fetch_jwks,
    )

    # O `Auth` que as rotas protegidas usam vive no módulo de infraestrutura;
    # aponta-se para o verificador de teste em vez de se falsear a dependência,
    # para o `/me` continuar a validar assinaturas a sério.
    from app.infrastructure import auth as auth_module

    auth_module.auth._verifier = verifier
    auth_module.auth._mapping = mapping

    service = SessionService(geea, verifier, mapping, AttemptLimiter(per_minute=10))
    app.dependency_overrides[get_session_service] = lambda: service

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
