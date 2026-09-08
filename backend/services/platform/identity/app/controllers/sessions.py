"""Abrir, renovar e terminar sessão."""

from fastapi import APIRouter, Request, Response, status

from app.controllers.dependencies import SessionServiceDep
from app.controllers.schemas import LoginRequest, PrincipalResponse, SessionResponse
from app.domain.errors import NoSessionError
from app.services.session_service import Session
from app.settings import settings

router = APIRouter(prefix="/sessions", tags=["sessions"])

#: O nome não diz «geea» nem «keycloak»: o cookie é da sessão do MozaOps, e
#: quem o emite pode mudar sem o browser dar por isso.
REFRESH_COOKIE = "mozaops_refresh"


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        REFRESH_COOKIE,
        token,
        # `httponly`: o JavaScript da página nunca lê este valor. É o que faz
        # com que um XSS no SPA não dê a ninguém uma sessão renovável.
        httponly=True,
        # `lax` e não `strict`: o operador que chega por um link de fora
        # continua com sessão, e o cookie não acompanha pedidos de escrita
        # vindos de outro sítio.
        samesite="lax",
        secure=settings.session_cookie_secure,
        path=settings.session_cookie_path,
    )


def _body(session: Session) -> SessionResponse:
    return SessionResponse(
        access_token=session.access_token,
        expires_in=session.expires_in,
        principal=PrincipalResponse(
            subject=session.principal.subject,
            username=session.principal.username,
            name=session.principal.name,
            email=session.principal.email,
            roles=sorted(session.principal.roles),
            department_code=session.principal.department_code,
            department=session.principal.department,
            function=session.principal.function,
        ),
    )


@router.post("", response_model=SessionResponse)
async def login(
    credentials: LoginRequest,
    request: Request,
    response: Response,
    sessions: SessionServiceDep,
) -> SessionResponse:
    client_ip = request.client.host if request.client else "0.0.0.0"  # noqa: S104
    session = await sessions.login(credentials.username, credentials.password, client_ip)
    _set_refresh_cookie(response, session.refresh_token)
    return _body(session)


@router.post("/refresh", response_model=SessionResponse)
async def refresh(
    request: Request,
    response: Response,
    sessions: SessionServiceDep,
) -> SessionResponse:
    token = request.cookies.get(REFRESH_COOKIE)
    if not token:
        raise NoSessionError

    session = await sessions.refresh(token)
    _set_refresh_cookie(response, session.refresh_token)
    return _body(session)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> Response:
    """Apaga o cookie deste lado.

    A sessão no GEEA continua aberta — terminá-la exige o `end_session` do
    realm, que é trabalho para quando o login for por reencaminhamento. Aqui,
    o que o operador perde é o acesso ao MozaOps, que é o que ele espera ao
    carregar em «sair».
    """
    response.delete_cookie(REFRESH_COOKIE, path=settings.session_cookie_path)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
