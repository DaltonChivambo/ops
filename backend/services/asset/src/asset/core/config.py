"""Definições do serviço asset (pydantic-settings, tudo por env var)."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "asset"
    environment: str = "development"
    port: int = 8003
    api_prefix: str = "/api/v1"
    log_level: str = "INFO"

    # Um schema e um role Postgres por serviço.
    database_url: str = "postgresql+psycopg://asset_svc:asset_dev_pw@localhost:5432/ops"
    db_schema: str = "asset"

    # Keycloak (externo). Cada serviço valida o token localmente contra o JWKS.
    keycloak_url: str = "https://keycloak.exemplo.local"
    keycloak_realm: str = "ops"
    keycloak_client_id: str = "ops-backend"
    jwks_url: str = ""          # vazio => derivado do url + realm
    jwt_algorithm: str = "RS256"

    # Observabilidade
    graylog_host: str | None = None
    graylog_port: int = 12201

    # Mensageria
    rabbitmq_url: str = "amqp://ops:ops_dev_pw@localhost:5672/"
    rabbitmq_exchange: str = "ops.events"
    rabbitmq_queue: str | None = None

    @property
    def issuer(self) -> str:
        return f"{self.keycloak_url}/realms/{self.keycloak_realm}"

    @property
    def jwks_endpoint(self) -> str:
        return self.jwks_url or f"{self.issuer}/protocol/openid-connect/certs"


@lru_cache
def get_settings() -> Settings:
    return Settings()
