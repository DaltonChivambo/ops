"""Configuração do serviço — variáveis de ambiente tipadas.

Esta lista é o contrato com o `.env.example` e com o `docker-compose.yml`: o que
o serviço lê está aqui, e o que aqui não está o serviço não lê. O
`extra="ignore"` esconde qualquer variável mal escrita, por isso a lista ser
completa é a única coisa que impede uma configuração silenciosamente ignorada —
foi o que aconteceu ao `LOG_LEVEL` até agora.
"""

import logging

from pydantic_settings import BaseSettings, SettingsConfigDict

from mozaops_libs.auth import AreaMapping, parse_area_map


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

    # ─── Autenticação ────────────────────────────────────────────────────
    # Estas são as MESMAS variáveis que o `platform/identity` declara, e no
    # compose recebem o mesmo `${...}`. Dois serviços a mapear áreas de
    # maneira diferente seria uma porta aberta no que ficasse para trás.
    auth_issuer: str = "http://geea-keycloak:8000/auth/realms/QAS"
    auth_jwks_url: str = "http://geea-keycloak:8000/auth/realms/QAS/protocol/openid-connect/certs"
    auth_allowed_azp: str = "qa-workflow-ui"

    auth_areas: str = "canais:3230"
    auth_area_users: str = ""

    #: A área a que **esta** automação pertence — a mesma que o `service.yaml`
    #: declara e que o catálogo do SPA mostra. É a única diferença de
    #: configuração de autenticação entre os dois serviços, e é o que o router
    #: exige a quem bate à porta.
    auth_service_area: str = "canais"

    def area_mapping(self) -> AreaMapping:
        return AreaMapping(
            by_unit=parse_area_map(self.auth_areas),
            by_user=parse_area_map(self.auth_area_users),
        )


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
