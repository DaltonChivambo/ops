"""As formas que entram e saem pela API. JSON em camelCase, Python em snake_case."""

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class Schema(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class LoginRequest(Schema):
    """As credenciais chegam **no corpo**, nunca na query string.

    O GEEA obriga-nos a pô-las num URL quando falamos com ele; o que o browser
    manda para aqui é outra coisa, e essa não tem de ficar no histórico nem
    nos logs de acesso de tudo o que houver pelo caminho.
    """

    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=256)


class PrincipalResponse(Schema):
    """Quem entrou, e o que é que isso lhe abre.

    `areas` são as do catálogo do MozaOps — as mesmas que a barra lateral do
    SPA mostra. `department`/`departmentCode` são a unidade orgânica tal como o
    GEEA a nomeia, e vão para o ecrã de «sem acesso»: quem lá cair precisa de
    dizer à coordenação em que unidade está registado.
    """

    subject: str
    username: str
    name: str
    email: str
    areas: list[str]
    department_code: str
    department: str
    function: str


class SessionResponse(Schema):
    """O token de acesso vai no corpo; o de renovação vai em cookie `HttpOnly`.

    O SPA guarda o de acesso em memória e perde-o ao recarregar a página — e é
    aí que o cookie serve: renova sem voltar a pedir a password, sem nunca
    ficar ao alcance de JavaScript.
    """

    access_token: str
    expires_in: int
    principal: PrincipalResponse
