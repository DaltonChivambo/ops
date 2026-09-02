"""Configuração do serviço — variáveis de ambiente tipadas.

Esta lista é o contrato com o `.env.example` e com o `docker-compose.yml`: o que
o serviço lê está aqui, e o que aqui não está o serviço não lê. O
`extra="ignore"` esconde qualquer variável mal escrita, por isso a lista ser
completa é a única coisa que impede uma configuração silenciosamente ignorada —
foi o que aconteceu ao `LOG_LEVEL` até agora.
"""

import logging

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    database_url: str = (
        "postgresql+asyncpg://closing_reconciliation:mude-me-em-producao"
        "@127.0.0.1:15432/mozaops_closing_reconciliation"
    )
    # Tamanho máximo de cada ficheiro carregado, verificado em
    # `controllers/executions.py` antes de o openpyxl lhe tocar.
    max_upload_mb: int = 64
    log_level: str = "INFO"


settings = Settings()


def configure_logging() -> None:
    """Aplica o `LOG_LEVEL` ao arranque.

    O `docker-compose.yml` passa esta variável ao contentor desde o primeiro dia
    e ninguém a lia: o serviço corria sempre no nível por omissão, e pô-la a
    `DEBUG` não fazia diferença nenhuma.
    """
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )
