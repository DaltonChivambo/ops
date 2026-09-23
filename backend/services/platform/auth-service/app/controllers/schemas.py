"""As formas que entram e saem pela API. JSON em camelCase, Python em snake_case."""

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class Schema(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class LoginRequest(Schema):
    """As credenciais chegam **no corpo**, nunca na query string."""

    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=256)


class PrincipalResponse(Schema):
    """Quem entrou, e o que é que isso lhe abre."""

    subject: str
    username: str
    name: str
    email: str
    areas: list[str]
    #: id da automação → `read` ou `write`.
    service_access: dict[str, str]
    department_code: str
    department: str
    function: str


class SessionResponse(Schema):
    """O token de acesso vai no corpo; o de renovação vai em cookie `HttpOnly`."""

    access_token: str
    expires_in: int
    principal: PrincipalResponse
