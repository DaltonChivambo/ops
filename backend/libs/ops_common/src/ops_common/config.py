"""Definições comuns a todos os serviços.

Cada serviço estende `BaseServiceSettings` no seu `core/config.py` e acrescenta o que for seu.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseServiceSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- identidade ---
    service_name: str = "servico"
    environment: str = "development"
    port: int = 8000

    # --- base de dados: um schema E um role por serviço ---
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/ops"
    db_schema: str = "public"
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_echo: bool = False

    # --- autenticação: validação local contra o JWKS do Auth ---
    jwks_url: str = "http://auth:8001/api/v1/.well-known/jwks.json"
    jwt_issuer: str = "ops-auth"
    jwt_audience: str = "ops-platform"
    jwt_algorithm: str = "RS256"

    # --- observabilidade ---
    log_level: str = "INFO"
    graylog_host: str | None = None
    graylog_port: int = 12201
    metrics_enabled: bool = True

    # --- mensageria ---
    rabbitmq_url: str = "amqp://ops:ops_dev_pw@rabbitmq:5672/"
    rabbitmq_exchange: str = "ops.events"
    rabbitmq_queue: str | None = None

    # --- API ---
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:4200"]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}


@lru_cache
def get_base_settings() -> BaseServiceSettings:
    return BaseServiceSettings()
