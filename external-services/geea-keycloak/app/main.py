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
from pathlib import Path

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI, Header, HTTPException

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "departamentos.json"

# ─── Credenciais aceites pelo login ──────────────────────────────────────
GEEA_REALM = os.environ.get("GEEA_KEYCLOAK_REALM", "QAS")
GEEA_USERNAME = os.environ.get("GEEA_KEYCLOAK_USERNAME", "geea.integracao")
GEEA_PASSWORD = os.environ.get("GEEA_KEYCLOAK_PASSWORD", "mude-me-em-producao")
GEEA_CLIENT_ID = os.environ.get("GEEA_KEYCLOAK_CLIENT_ID", "qa-workflow-ui")
GEEA_CLIENT_SECRET = os.environ.get("GEEA_KEYCLOAK_CLIENT_SECRET", "mude-me-em-producao")

TOKEN_TTL_SECONDS = int(os.environ.get("GEEA_KEYCLOAK_TOKEN_TTL", "18000"))
# O `iss` dos tokens e o `jwks_uri` do documento de descoberta. Por omissão é
# o endereço do próprio mock dentro da rede `mozaops`, e não o do GEEA real
# (`svdcpapq70:10080`): em desenvolvimento quem emite é este container, e quem
# valida tem de conseguir lá chegar. Trocar esta variável muda os dois sítios
# ao mesmo tempo, que é o que os mantém coerentes.
ISS_HOST = os.environ.get("GEEA_KEYCLOAK_ISS_HOST", "geea-keycloak:8000")
ALLOWED_ORIGIN = os.environ.get("GEEA_KEYCLOAK_ALLOWED_ORIGIN", "http://svdcpapq51:8085")

# ─── Perfil do utilizador de mock — devolvido nas claims do token ────────
# Valores por omissão tal como no exemplo real fornecido; ajusta por env se
# precisares de simular outra pessoa/departamento.
MOCK_SUB = os.environ.get("GEEA_MOCK_SUB", "6961d9f6-5529-457b-93cb-db82230a00cb")
MOCK_NAME = os.environ.get("GEEA_MOCK_NAME", "Dalton Chivambo Chivambo")
MOCK_GIVEN_NAME = os.environ.get("GEEA_MOCK_GIVEN_NAME", "Dalton Chivambo")
MOCK_FAMILY_NAME = os.environ.get("GEEA_MOCK_FAMILY_NAME", "Chivambo")
MOCK_EMAIL = os.environ.get("GEEA_MOCK_EMAIL", "dalton.chivambo@mozabanco.co.mz")
MOCK_FUNCTION = os.environ.get("GEEA_MOCK_FUNCTION", "Director")
MOCK_DEPARTMENT_CODE = os.environ.get("GEEA_MOCK_DEPARTMENT_CODE", "2350")
MOCK_DEPARTMENT = os.environ.get("GEEA_MOCK_DEPARTMENT", "Departamento de Apoio Operacional")
MOCK_WORKSTATION = os.environ.get("GEEA_MOCK_WORKSTATION", "WSEDE47W")
MOCK_EMPLOYEE_ID = os.environ.get("GEEA_MOCK_EMPLOYEE_ID", "1926")
MOCK_TELEPHONE = os.environ.get("GEEA_MOCK_TELEPHONE", "714068")
MOCK_SCOPE = os.environ.get("GEEA_MOCK_SCOPE", "manage-clients AD email profile")
MOCK_REALM_ROLES = [
    "search_processes",
    "idm_menu",
    "manage_function",
    "manage_organicUnit",
    "offline_access",
    "work_queue",
    "process_parent",
    "manage_aml_entities",
    "kie-server",
    "manage_employee",
]
MOCK_ACCOUNT_ROLES = ["manage-account", "manage-account-links", "view-profile"]

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
    realm: str, client_id: str, username: str, jti: str, session_state: str, iat: int, exp: int
) -> dict:
    return {
        "jti": jti,
        "exp": exp,
        "nbf": 0,
        "iat": iat,
        "iss": _issuer(realm),
        "aud": "account",
        "sub": MOCK_SUB,
        "typ": "Bearer",
        "azp": client_id,
        "nonce": None,
        "auth_time": 0,
        "session_state": session_state,
        "at_hash": None,
        "c_hash": None,
        "name": MOCK_NAME,
        "given_name": MOCK_GIVEN_NAME,
        "family_name": MOCK_FAMILY_NAME,
        "middle_name": None,
        "nickname": None,
        "preferred_username": username,
        "profile": None,
        "picture": None,
        "website": None,
        "email": MOCK_EMAIL,
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
        "resource_access": {"account": {"roles": MOCK_ACCOUNT_ROLES, "verify_caller": None}},
        "authorization": None,
        "cnf": None,
        "scope": MOCK_SCOPE,
        "function": MOCK_FUNCTION,
        "departmentCode": MOCK_DEPARTMENT_CODE,
        "workstation": MOCK_WORKSTATION,
        "Employee ID": MOCK_EMPLOYEE_ID,
        "telephone": MOCK_TELEPHONE,
        "department": MOCK_DEPARTMENT,
    }


def _refresh_claims(
    realm: str, client_id: str, jti: str, session_state: str, iat: int, exp: int
) -> dict:
    issuer = _issuer(realm)
    return {
        "jti": jti,
        "exp": exp,
        "nbf": 0,
        "iat": iat,
        "iss": issuer,
        "aud": issuer,
        "sub": MOCK_SUB,
        "typ": "Refresh",
        "azp": client_id,
        "auth_time": 0,
        "session_state": session_state,
        "realm_access": {"roles": MOCK_REALM_ROLES, "verify_caller": None},
        "resource_access": {"account": {"roles": MOCK_ACCOUNT_ROLES, "verify_caller": None}},
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
    if (
        realm != GEEA_REALM
        or username != GEEA_USERNAME
        or password != GEEA_PASSWORD
        or clientId != GEEA_CLIENT_ID
        or clientSecret != GEEA_CLIENT_SECRET
    ):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    jti = str(uuid.uuid4())
    session_state = str(uuid.uuid4())
    iat = int(time.time())
    exp = iat + TOKEN_TTL_SECONDS

    access_claims = _access_claims(realm, clientId, username, jti, session_state, iat, exp)
    id_claims = dict(access_claims)
    refresh_claims = _refresh_claims(
        realm, clientId, str(uuid.uuid4()), session_state, iat, exp
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
