"""Configuração do serviço — variáveis de ambiente tipadas.

Esta lista é o contrato com o `.env.example` e com o `docker-compose.yml`: o
que o serviço lê está aqui, e o que aqui não está o serviço não lê, porque o
`extra="ignore"` esconde qualquer variável mal escrita.

As variáveis `auth_*` são **as mesmas** que o `closing-credit-validation`
declara, e no compose recebem o mesmo `${...}`: dois serviços a mapear áreas
de maneira diferente seria uma porta aberta num deles.
"""

import logging

from pydantic_settings import BaseSettings, SettingsConfigDict

from mozaops_libs.auth import AreaMapping, parse_area_map


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    # ─── Validação dos tokens ────────────────────────────────────────────
    auth_issuer: str = "http://geea-keycloak:8000/auth/realms/QAS"
    auth_jwks_url: str = "http://geea-keycloak:8000/auth/realms/QAS/protocol/openid-connect/certs"
    #: Clientes cujos tokens aceitamos. Um token legítimo do GEEA emitido para
    #: outra aplicação do banco não serve para entrar aqui.
    auth_allowed_azp: str = "qa-workflow-ui"

    # ─── Mapa de áreas ───────────────────────────────────────────────────
    #: `area:unidade,unidade;area:unidade`. A área é a do catálogo do MozaOps
    #: (a mesma da barra lateral do SPA); as unidades são os códigos que o GEEA
    #: manda em `departmentCode`. Sem entrada aqui, ninguém entra em lado
    #: nenhum — é de propósito, ver `mozaops_libs/auth/areas.py`.
    auth_areas: str = "channels:3230"
    #: `area:username,username`. O acréscimo para quem está registado noutra
    #: unidade mas trabalha nesta. Vazio é o estado normal.
    auth_area_users: str = ""

    # ─── Ligação ao GEEA ─────────────────────────────────────────────────
    geea_ssologin_url: str = "http://geea-keycloak:8000/geea/idmUtils/SSOLogin"
    # `noqa: S105` nas duas linhas seguintes: o ruff vê «token» e «secret» no
    # nome e assume segredo em código. Uma é um endereço; a outra é o valor de
    # marcação que o compose substitui — o mesmo padrão do `database_url` do
    # outro serviço, que só não é assinalado por não ter a palavra no nome.
    geea_token_url: str = "http://geea-keycloak:8000/auth/realms/QAS/protocol/openid-connect/token"  # noqa: S105
    geea_realm: str = "QAS"
    geea_client_id: str = "qa-workflow-ui"
    geea_client_secret: str = "mude-me-em-producao"  # noqa: S105

    # ─── Sessão ──────────────────────────────────────────────────────────
    #: O cookie de renovação só viaja em HTTPS. Fica `False` só em
    #: desenvolvimento, onde o Traefik ainda serve em claro.
    session_cookie_secure: bool = True
    #: O `Path` do cookie, na **vista do browser** — que inclui o `/api` que o
    #: Traefik corta antes de o pedido chegar aqui. Limitá-lo é o que impede o
    #: cookie de acompanhar os pedidos às automações, que usam o cabeçalho.
    #: É configuração e não constante porque quem fala com o serviço sem o
    #: proxy à frente (testes, `curl` na porta de dev) vê outro caminho.
    session_cookie_path: str = "/api/identity"
    #: Tentativas de login por utilizador e por minuto. Sem isto, o endpoint é
    #: um oráculo de força bruta contra contas do domínio — e o bloqueio que
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

    # ─────────────────────────────────────────────────────────────────────
    # O `httpx` regista cada pedido ao nível INFO, com o URL inteiro. O URL
    # do SSOLogin leva a **password do domínio** na query string, por
    # exigência do contrato do GEEA. Sem isto, uma password real por cada
    # login ficava nos logs do container e em tudo o que os recolha.
    #
    # Não é ajuste de verbosidade: é a razão de o serviço poder existir.
    # ─────────────────────────────────────────────────────────────────────
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
