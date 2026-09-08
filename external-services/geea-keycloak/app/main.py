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
from fastapi import FastAPI, Header, HTTPException

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "departamentos.json"

# ─── Credenciais aceites pelo login ──────────────────────────────────────
GEEA_REALM = os.environ.get("GEEA_KEYCLOAK_REALM", "QAS")
GEEA_USERNAME = os.environ.get("GEEA_KEYCLOAK_USERNAME", "geea.integracao")
GEEA_PASSWORD = os.environ.get("GEEA_KEYCLOAK_PASSWORD", "mude-me-em-producao")
GEEA_CLIENT_ID = os.environ.get("GEEA_KEYCLOAK_CLIENT_ID", "qa-workflow-ui")
GEEA_CLIENT_SECRET = os.environ.get("GEEA_KEYCLOAK_CLIENT_SECRET", "mude-me-em-producao")

# Assina os JWT de mock. Não precisa de bater certo com a chave real — só
# quem faz login neste mock é que vai validar tokens deste mock.
JWT_SECRET = os.environ.get("GEEA_KEYCLOAK_JWT_SECRET", "mude-me-em-producao")
TOKEN_TTL_SECONDS = int(os.environ.get("GEEA_KEYCLOAK_TOKEN_TTL", "18000"))
ISS_HOST = os.environ.get("GEEA_KEYCLOAK_ISS_HOST", "svdcpapq70:10080")
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

    access_jwt = jwt.encode(access_claims, JWT_SECRET, algorithm="HS256")
    refresh_jwt = jwt.encode(refresh_claims, JWT_SECRET, algorithm="HS256")

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
        jwt.decode(token, JWT_SECRET, algorithms=["HS256"], options={"verify_aud": False})
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado") from exc


@app.get("/departamentos")
def get_departamentos(authorization: str | None = Header(default=None)) -> list[dict]:
    _require_token(authorization)
    return DEPARTAMENTOS


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
