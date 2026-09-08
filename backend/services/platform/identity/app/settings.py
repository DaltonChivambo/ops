"""Configuração do serviço — variáveis de ambiente tipadas.

Esta lista é o contrato com o `.env.example` e com o `docker-compose.yml`: o
que o serviço lê está aqui, e o que aqui não está o serviço não lê, porque o
`extra="ignore"` esconde qualquer variável mal escrita.

As variáveis `auth_*` são **as mesmas** que o `closing-credit-validation`
declara, e no compose recebem o mesmo `${...}`: dois serviços a mapear papéis
de maneira diferente seria uma porta aberta num deles.
"""

import logging

from pydantic_settings import BaseSettings, SettingsConfigDict

from mozaops_libs.auth import RoleMapping, parse_set


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    # ─── Validação dos tokens ────────────────────────────────────────────
    auth_issuer: str = "http://geea-keycloak:8000/auth/realms/QAS"
    auth_jwks_url: str = "http://geea-keycloak:8000/auth/realms/QAS/protocol/openid-connect/certs"
    #: Clientes cujos tokens aceitamos. Um token legítimo do GEEA emitido para
    #: outra aplicação do banco não serve para entrar aqui.
    auth_allowed_azp: str = "qa-workflow-ui"

    # ─── Mapa de papéis ──────────────────────────────────────────────────
    auth_supervisor_users: str = ""
    auth_auditor_users: str = ""
    auth_operator_users: str = ""
    auth_operator_departments: str = "2350"
    auth_supervisor_functions: str = "Director,Chefe"
    auth_role_claim_prefix: str = "mozaops_"

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

    def role_mapping(self) -> RoleMapping:
        return RoleMapping(
            supervisor_users=parse_set(self.auth_supervisor_users),
            auditor_users=parse_set(self.auth_auditor_users),
            operator_users=parse_set(self.auth_operator_users),
            operator_departments=parse_set(self.auth_operator_departments),
            supervisor_functions=parse_set(self.auth_supervisor_functions),
            role_claim_prefix=self.auth_role_claim_prefix,
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
