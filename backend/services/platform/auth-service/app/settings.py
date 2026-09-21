"""Configuração do serviço — variáveis de ambiente tipadas.

As variáveis `auth_*` são as mesmas que o `pos-closing-credit-validation`
declara, e no compose recebem o mesmo `${...}`: dois serviços a mapear áreas de
maneira diferente seria uma porta aberta num deles.
"""

import logging

from pydantic_settings import BaseSettings, SettingsConfigDict

from mozaops_libs.auth import AreaMapping, parse_area_map


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    # ─── Validação dos tokens ────────────────────────────────────────────
    auth_issuer: str = "http://geea-keycloak:8000/auth/realms/QAS"
    auth_jwks_url: str = "http://geea-keycloak:8000/auth/realms/QAS/protocol/openid-connect/certs"
    auth_allowed_azp: str = "qa-mozaops"

    # ─── Mapa de áreas ───────────────────────────────────────────────────
    # Rede por baixo dos papéis do realm, que são a fonte principal e não se
    # configuram aqui — ver `mozaops_libs/auth/areas.py`.
    #: `area:unidade,unidade;area:unidade`, com os códigos do `departmentCode`.
    auth_areas: str = "channels:3230"
    #: `area:username,username`. Vazio é o estado normal.
    auth_area_users: str = ""

    # ─── Ligação ao GEEA ─────────────────────────────────────────────────
    geea_ssologin_url: str = "http://geea-keycloak:8000/geea/idmUtils/SSOLogin"
    # `noqa: S105`: o ruff vê «token» e «secret» no nome e assume segredo em
    # código. Uma é um endereço; a outra, o valor que o compose substitui.
    geea_token_url: str = "http://geea-keycloak:8000/auth/realms/QAS/protocol/openid-connect/token"  # noqa: S105
    geea_realm: str = "QAS"
    geea_client_id: str = "qa-mozaops"
    geea_client_secret: str = "mude-me-em-producao"  # noqa: S105

    # ─── Sessão ──────────────────────────────────────────────────────────
    #: `False` só em desenvolvimento, onde o Traefik ainda serve em claro.
    session_cookie_secure: bool = True
    #: O `Path` na vista do browser, com o `/api` que o Traefik corta. Limitá-lo
    #: impede o cookie de acompanhar os pedidos às automações. É configuração
    #: porque quem fala com o serviço sem proxy à frente vê outro caminho.
    session_cookie_path: str = "/api/auth-service"
    #: Sem isto o endpoint é um oráculo de força bruta, e o bloqueio que
    #: acontecer é no AD do banco, não aqui.
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

    # O `httpx` regista cada pedido ao nível INFO, com o URL inteiro — e o URL
    # do SSOLogin leva a password do domínio na query string, por exigência do
    # contrato do GEEA. Sem isto, uma password real por login ia para os logs.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
