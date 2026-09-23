"""Configuração do serviço — variáveis de ambiente tipadas."""

import logging

from mozaops_libs.auth import AreaMapping, parse_area_map
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    database_url: str
    # Verificado em `controllers/executions.py` antes de o leitor tocar no ficheiro.
    max_upload_mb: int = 64
    log_level: str = "INFO"

    # ─── Autenticação ────────────────────────────────────────────────────
    # As mesmas variáveis que o `platform/auth-service` declara, com o mesmo `${...}`.
    auth_issuer: str = "http://geea-keycloak:8000/auth/realms/QAS"
    auth_jwks_url: str = "http://geea-keycloak:8000/auth/realms/QAS/protocol/openid-connect/certs"
    auth_allowed_azp: str = "qa-mozaops"
    #: O cliente cujos papéis concedem acesso. Não é o `azp` do token.
    auth_client_id: str = "qa-mozaops"

    auth_areas: str = "channels:3230"
    auth_area_users: str = ""

    #: A área desta automação, a mesma do `service.yaml`. É o que o router exige.
    auth_service_area: str = "channels"

    #: O id desta automação, o que os papéis `service:<id>:<read|write>` referem.
    auth_service_id: str = "pos-closing-credit-validation"

    def area_mapping(self) -> AreaMapping:
        return AreaMapping(
            by_unit=parse_area_map(self.auth_areas),
            by_user=parse_area_map(self.auth_area_users),
        )


settings = Settings()


def configure_logging() -> None:
    """Aplica o `LOG_LEVEL` ao arranque."""
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )
