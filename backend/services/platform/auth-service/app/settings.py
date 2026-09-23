"""Configuração do serviço — variáveis de ambiente tipadas."""

import logging

from pydantic_settings import BaseSettings, SettingsConfigDict

from mozaops_libs.auth import AreaMapping, parse_area_map


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    # ─── Validação dos tokens ────────────────────────────────────────────
    auth_issuer: str = "http://geea-keycloak:8000/auth/realms/QAS"
    auth_jwks_url: str = "http://geea-keycloak:8000/auth/realms/QAS/protocol/openid-connect/certs"
    auth_allowed_azp: str = "qa-mozaops"
    #: O cliente cujos papéis concedem acesso. Não é o `azp` do token.
    auth_client_id: str = "qa-mozaops"

    # ─── Mapa de áreas ───────────────────────────────────────────────────
    # Rede por baixo dos papéis do realm — ver `mozaops_libs/auth/areas.py`.
    #: `area:unidade,unidade;area:unidade`, com os códigos do `departmentCode`.
    auth_areas: str = "channels:3230"
    #: `area:username,username`. Vazio é o estado normal.
    auth_area_users: str = ""

    # ─── Ligação ao GEEA ─────────────────────────────────────────────────
    geea_ssologin_url: str = "http://geea-keycloak:8000/geea/idmUtils/SSOLogin"
    # `noqa: S105`: o ruff vê «token»/«secret» no nome; uma é URL, a outra vem do compose.
    geea_token_url: str = "http://geea-keycloak:8000/auth/realms/QAS/protocol/openid-connect/token"  # noqa: S105
    geea_realm: str = "QAS"
    geea_client_id: str = "qa-mozaops"
    geea_client_secret: str

    # ─── Sessão ──────────────────────────────────────────────────────────
    #: `False` só em desenvolvimento, onde o Traefik ainda serve em claro.
    session_cookie_secure: bool = True
    #: O caminho na vista do browser, com o `/api` que o Traefik corta.
    session_cookie_path: str = "/api/auth-service"
    #: Trava a adivinhação de passwords; o bloqueio a sério é o do AD.
    login_attempts_per_minute: int = 10

    log_level: str = "INFO"

    def area_mapping(self) -> AreaMapping:
        return AreaMapping(
            by_unit=parse_area_map(self.auth_areas),
            by_user=parse_area_map(self.auth_area_users),
        )


settings = Settings()


def configure_logging() -> None:
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )

    # O httpx regista o URL inteiro ao nível INFO, e o do SSOLogin leva a password.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
