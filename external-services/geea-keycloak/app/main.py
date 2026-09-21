"""GEEA_KEYCLOAK — serviço externo simulado.

Mock standalone da fonte de dados organizacionais do GEEA: replica o
contrato do `SSOLogin` real (GET com credenciais na query string, corpo de
resposta com `accessToken`/`idToken`/`output`) e devolve a lista de
unidades organizacionais depois de login bem-sucedido. Não faz parte da
aplicação MozaOps — vive fora de `backend/` de propósito, para não se
confundir com um serviço nosso.
"""

import json
import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI, Form, Header, HTTPException

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "departamentos.json"

# ─── Credenciais aceites pelo login ──────────────────────────────────────
# Os utilizadores estão mais abaixo, em `USERS`. A password é uma só para
# todos: é um mock, e ter uma por pessoa só daria mais coisas para decorar.
GEEA_REALM = os.environ.get("GEEA_KEYCLOAK_REALM", "QAS")
GEEA_PASSWORD = os.environ.get("GEEA_KEYCLOAK_PASSWORD", "mude-me-em-producao")
GEEA_CLIENT_ID = os.environ.get("GEEA_KEYCLOAK_CLIENT_ID", "qa-mozaops")
GEEA_CLIENT_SECRET = os.environ.get("GEEA_KEYCLOAK_CLIENT_SECRET", "mude-me-em-producao")

TOKEN_TTL_SECONDS = int(os.environ.get("GEEA_KEYCLOAK_TOKEN_TTL", "18000"))
# O `iss` dos tokens e o `jwks_uri` do documento de descoberta. Por omissão é
# o endereço do próprio mock dentro da rede `mozaops`, e não o do GEEA real
# (`svdcpapq70:10080`): em desenvolvimento quem emite é este container, e quem
# valida tem de conseguir lá chegar. Trocar esta variável muda os dois sítios
# ao mesmo tempo, que é o que os mantém coerentes.
ISS_HOST = os.environ.get("GEEA_KEYCLOAK_ISS_HOST", "geea-keycloak:8000")
ALLOWED_ORIGIN = os.environ.get("GEEA_KEYCLOAK_ALLOWED_ORIGIN", "http://svdcpapq51:8085")

MOCK_SCOPE = os.environ.get("GEEA_MOCK_SCOPE", "AD email profile")
# Os papéis do sistema de workflow do banco. São iguais para toda a gente e não
# abrem nada no MozaOps — estão aqui porque vêm no token real.
MOCK_REALM_ROLES = [
    "search_processes",
    "idm_menu",
    "channels",
    "manage_function",
    "manage_organicUnit",
    "offline_access",
    "work_queue",
    "process_parent",
    "kie-server",
    "manage_employee",
]
MOCK_ACCOUNT_ROLES = ["manage-account", "manage-account-links", "view-profile"]


# ─── Utilizadores ────────────────────────────────────────────────────────
@dataclass(frozen=True)
class MockUser:
    """Uma pessoa do directório, com as claims que o token dela leva.

    `roles` são os papéis do cliente `qa-mozaops`, e é de lá que o MozaOps tira
    as áreas: cada papel tem o nome da área que abre, e o `all-areas` abre-as
    todas. Mudar esta lista é mudar o que a pessoa vê. Ver
    `mozaops_libs/auth/areas.py`.
    """

    username: str
    sub: str
    name: str
    given_name: str
    family_name: str
    email: str
    function: str
    department_code: str
    department: str
    workstation: str
    employee_id: str
    telephone: str
    roles: list[str]


# Dois, e não um: com um utilizador só nunca se vê o que o MozaOps faz a quem
# não é da área — que é metade do comportamento que há para testar.
#
# O `m001926` é real: as claims são as que o QAS devolve. O `m002000` é
# inventado, e existe para haver alguém com menos acesso do que outro.
USERS: dict[str, MockUser] = {
    user.username: user
    for user in (
        MockUser(
            username="m001926",
            sub="6961d9f6-5529-457b-93cb-db82230a00cb",
            name="Dalton Chivambo Chivambo",
            given_name="Dalton Chivambo",
            family_name="Chivambo",
            email="dalton.chivambo@mozabanco.co.mz",
            function="Director",
            department_code="2350",
            department="Departamento de Apoio Operacional",
            workstation="WSEDE47W",
            employee_id="1926",
            telephone="714068",
            # Um papel só, e não a lista das áreas: `all-areas` abre o sistema
            # inteiro, incluindo o que ainda não foi construído — é o acesso
            # total, e não a soma do que hoje existe.
            roles=["all-areas"],
        ),
        MockUser(
            username="m002000",
            sub="4b2f7a10-9c3d-4e58-8f61-0d7a5c2e9b34",
            name="John Doe",
            given_name="John Doe",
            family_name="Doe",
            email="john.doe@mozabanco.co.mz",
            function="Técnico",
            department_code="3230",
            department="Canais e Serviços de Integração",
            workstation="WSEDE12A",
            employee_id="2000",
            telephone="714099",
            # Só canais: é o que separa este do outro.
            roles=["channels"],
        ),
    )
}

# O token de renovação não leva `preferred_username` — o Keycloak real também
# não lho põe — por isso quem volta é identificado pelo `sub`.
USERS_BY_SUB = {user.sub: user for user in USERS.values()}

app = FastAPI(title="GEEA_KEYCLOAK")

DEPARTAMENTOS = json.loads(DATA_FILE.read_text(encoding="utf-8"))

# ─── Chaves de assinatura ────────────────────────────────────────────────
# RS256 com par gerado ao arranque, e não HS256 com segredo partilhado: é
# assim que o GEEA real assina, e quem consome valida sempre pelo JWKS. Sem
# isto, o backend precisaria de um ramo «em dev é de outra maneira» — que é
# exactamente o que o proxy do frontend e o Traefik evitam ao manterem a
# mesma topologia dos dois lados.
#
# O par muda a cada reinício, e é de propósito: obriga quem valida a
# refrescar o JWKS quando aparece um `kid` desconhecido, em vez de assumir
# que a chave que leu uma vez serve para sempre.
_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_public_key = _private_key.public_key()
KID = uuid.uuid4().hex

_JWK = {
    **json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(_public_key)),
    "kid": KID,
    "use": "sig",
    "alg": "RS256",
}
# O `to_jwk` do PyJWT acrescenta `key_ops`, que um Keycloak não publica — e o
# RFC 7517 pede que `use` e `key_ops` não apareçam juntos sem necessidade.
_JWK.pop("key_ops", None)


def _issuer(realm: str) -> str:
    return f"http://{ISS_HOST}/auth/realms/{realm}"


def _access_claims(
    realm: str, client_id: str, user: MockUser, jti: str, session_state: str, iat: int, exp: int
) -> dict:
    return {
        "jti": jti,
        "exp": exp,
        "nbf": 0,
        "iat": iat,
        "iss": _issuer(realm),
        "aud": "account",
        "sub": user.sub,
        "typ": "Bearer",
        "azp": client_id,
        "nonce": None,
        "auth_time": 0,
        "session_state": session_state,
        "at_hash": None,
        "c_hash": None,
        "name": user.name,
        "given_name": user.given_name,
        "family_name": user.family_name,
        "middle_name": None,
        "nickname": None,
        "preferred_username": user.username,
        "profile": None,
        "picture": None,
        "website": None,
        "email": user.email,
        "email_verified": False,
        "gender": None,
        "birthdate": None,
        "zoneinfo": None,
        "locale": None,
        "phone_number": None,
        "phone_number_verified": None,
        "address": None,
        "updated_at": None,
        "claims_locales": None,
        "acr": "1",
        "s_hash": None,
        "trusted-certs": None,
        "allowed-origins": [ALLOWED_ORIGIN],
        "realm_access": {"roles": MOCK_REALM_ROLES, "verify_caller": None},
        "resource_access": {
            client_id: {"roles": user.roles, "verify_caller": None},
            "account": {"roles": MOCK_ACCOUNT_ROLES, "verify_caller": None},
        },
        "authorization": None,
        "cnf": None,
        "scope": MOCK_SCOPE,
        "function": user.function,
        "departmentCode": user.department_code,
        "workstation": user.workstation,
        "Employee ID": user.employee_id,
        "telephone": user.telephone,
        "department": user.department,
    }


def _refresh_claims(
    realm: str, client_id: str, user: MockUser, jti: str, session_state: str, iat: int, exp: int
) -> dict:
    issuer = _issuer(realm)
    return {
        "jti": jti,
        "exp": exp,
        "nbf": 0,
        "iat": iat,
        "iss": issuer,
        "aud": issuer,
        "sub": user.sub,
        "typ": "Refresh",
        "azp": client_id,
        "auth_time": 0,
        "session_state": session_state,
        "realm_access": {"roles": MOCK_REALM_ROLES, "verify_caller": None},
        "resource_access": {
            client_id: {"roles": user.roles, "verify_caller": None},
            "account": {"roles": MOCK_ACCOUNT_ROLES, "verify_caller": None},
        },
        "scope": MOCK_SCOPE,
    }


@app.get("/geea/idmUtils/SSOLogin")
def sso_login(
    realm: str,
    username: str,
    password: str,
    clientId: str,
    clientSecret: str,
    clientIpAdress: str | None = None,
) -> dict:
    user = USERS.get(username)
    if (
        realm != GEEA_REALM
        or user is None
        or password != GEEA_PASSWORD
        or clientId != GEEA_CLIENT_ID
        or clientSecret != GEEA_CLIENT_SECRET
    ):
        # Uma mensagem só: dizer «esse utilizador não existe» contaria a quem
        # tenta adivinhar contas quais é que existem. O real também não conta.
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    jti = str(uuid.uuid4())
    session_state = str(uuid.uuid4())
    iat = int(time.time())
    exp = iat + TOKEN_TTL_SECONDS

    access_claims = _access_claims(realm, clientId, user, jti, session_state, iat, exp)
    id_claims = dict(access_claims)
    refresh_claims = _refresh_claims(
        realm, clientId, user, str(uuid.uuid4()), session_state, iat, exp
    )

    headers = {"kid": KID}
    access_jwt = jwt.encode(access_claims, _private_key, algorithm="RS256", headers=headers)
    refresh_jwt = jwt.encode(refresh_claims, _private_key, algorithm="RS256", headers=headers)

    return {
        "createdOn": None,
        "modifiedOn": None,
        "modifiedBy": None,
        "createdBy": None,
        "accessToken": access_claims,
        "idToken": id_claims,
        "output": {
            "accessToken": access_jwt,
            "expiresIn": str(TOKEN_TTL_SECONDS),
            "refreshExpiresIn": str(TOKEN_TTL_SECONDS),
            "refreshToken": refresh_jwt,
            "tokenType": "bearer",
            "error": None,
            "errorDescription": None,
        },
        "clientIpAdress": clientIpAdress,
    }


@app.post("/auth/realms/{realm}/protocol/openid-connect/token")
def token(
    realm: str,
    grant_type: str = Form(),
    refresh_token: str = Form(),
    client_id: str = Form(),
    client_secret: str = Form(default=""),
) -> dict:
    """A rota normal do OIDC, para renovar.

    O `SSOLogin` devolve um `refreshToken` mas não tem por onde o trocar — quem
    o aceita é o realm, aqui. Como o serviço `auth-service` do MozaOps renova por
    esta rota, sem ela o mock não conseguia exercitar metade do ciclo de vida
    de uma sessão.

    Responde em snake_case, como um Keycloak — e não no camelCase do wrapper.
    """
    if realm != GEEA_REALM or grant_type != "refresh_token" or client_id != GEEA_CLIENT_ID:
        raise HTTPException(status_code=400, detail="invalid_request")
    if client_secret != GEEA_CLIENT_SECRET:
        raise HTTPException(status_code=401, detail="invalid_client")

    try:
        claims = jwt.decode(
            refresh_token, _public_key, algorithms=["RS256"], options={"verify_aud": False}
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=400, detail="invalid_grant") from exc

    if claims.get("typ") != "Refresh":
        raise HTTPException(status_code=400, detail="invalid_grant")

    user = USERS_BY_SUB.get(str(claims.get("sub") or ""))
    if user is None:
        raise HTTPException(status_code=400, detail="invalid_grant")

    iat = int(time.time())
    exp = iat + TOKEN_TTL_SECONDS
    session_state = str(claims.get("session_state") or uuid.uuid4())

    headers = {"kid": KID}
    access_claims = _access_claims(
        realm, client_id, user, str(uuid.uuid4()), session_state, iat, exp
    )
    refresh_claims = _refresh_claims(
        realm, client_id, user, str(uuid.uuid4()), session_state, iat, exp
    )

    return {
        "access_token": jwt.encode(
            access_claims, _private_key, algorithm="RS256", headers=headers
        ),
        "refresh_token": jwt.encode(
            refresh_claims, _private_key, algorithm="RS256", headers=headers
        ),
        "expires_in": TOKEN_TTL_SECONDS,
        "refresh_expires_in": TOKEN_TTL_SECONDS,
        "token_type": "Bearer",
        "session_state": session_state,
        "scope": MOCK_SCOPE,
    }


def _require_token(authorization: str | None) -> None:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token em falta")

    token = authorization.removeprefix("Bearer ")
    try:
        # `verify_aud` desligado: o token traz `aud: "account"`, e o PyJWT
        # recusa um token com `aud` a quem não lhe passe a audiência esperada.
        jwt.decode(token, _public_key, algorithms=["RS256"], options={"verify_aud": False})
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado") from exc


@app.get("/departamentos")
def get_departamentos(authorization: str | None = Header(default=None)) -> list[dict]:
    _require_token(authorization)
    return DEPARTAMENTOS


@app.get("/auth/realms/{realm}/protocol/openid-connect/certs")
def jwks(realm: str) -> dict:
    """As chaves públicas, no caminho em que um Keycloak as publica.

    É por aqui que o backend do MozaOps valida assinaturas — nunca por um
    segredo partilhado.
    """
    return {"keys": [_JWK]}


@app.get("/auth/realms/{realm}/.well-known/openid-configuration")
def discovery(realm: str) -> dict:
    """O documento de descoberta, reduzido ao que interessa a quem valida."""
    issuer = _issuer(realm)
    return {
        "issuer": issuer,
        "jwks_uri": f"{issuer}/protocol/openid-connect/certs",
        "id_token_signing_alg_values_supported": ["RS256"],
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
