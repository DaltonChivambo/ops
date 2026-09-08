"""Um emissor de tokens de mentira, para testar a validação sem rede.

Gera um par RSA no arranque da sessão de testes e assina tokens com ele,
publicando o JWKS como o GEEA o publicaria. O verificador nunca sabe que não
está a falar com ninguém: recebe o mesmo documento que receberia por HTTP.
"""

import json
import time
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

ISSUER = "http://geea-keycloak:8000/auth/realms/QAS"
AZP = "mozaops-web"


class FakeIssuer:
    def __init__(self, kid: str = "chave-1"):
        self.kid = kid
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.fetches = 0

    def jwks(self) -> dict[str, Any]:
        jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(self.private_key.public_key()))
        jwk.pop("key_ops", None)
        return {"keys": [{**jwk, "kid": self.kid, "use": "sig", "alg": "RS256"}]}

    async def fetch(self) -> dict[str, Any]:
        self.fetches += 1
        return self.jwks()

    def token(self, **overrides: Any) -> str:
        # Fora das claims antes de as juntar: senão o cabeçalho ia parar ao
        # corpo do token, e o teste passava a validar outra coisa.
        headers = overrides.pop("_headers", {"kid": self.kid})
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
        return jwt.encode(claims, self.private_key, algorithm="RS256", headers=headers)


@pytest.fixture
def issuer() -> FakeIssuer:
    return FakeIssuer()
