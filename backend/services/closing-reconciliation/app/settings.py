"""Configuração do serviço — variáveis de ambiente tipadas."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    database_url: str = (
        "postgresql+asyncpg://closing_reconciliation:mude-me-em-producao"
        "@127.0.0.1:15432/mozaops_closing_reconciliation"
    )
    max_upload_mb: int = 64


settings = Settings()
