"""Abrir e renovar sessões. O caso de uso, sem saber o que é um pedido HTTP."""

import time
from collections import deque
from dataclasses import dataclass
from typing import Any

from app.domain.errors import InvalidCredentialsError, TooManyAttemptsError
from app.infrastructure.geea_client import GeeaClient
from mozaops_libs.auth import AreaMapping, AuthError, Principal, TokenVerifier
from mozaops_libs.auth import principal_from_claims as build_principal


@dataclass(frozen=True, slots=True)
class Session:
    principal: Principal
    access_token: str
    refresh_token: str
    expires_in: int


class AttemptLimiter:
    """Janela deslizante por utilizador, em memória."""

    def __init__(self, per_minute: int):
        self._per_minute = per_minute
        self._attempts: dict[str, deque[float]] = {}

    def check(self, key: str) -> None:
        if self._per_minute <= 0:
            return

        now = time.monotonic()
        window = self._attempts.setdefault(key, deque())
        while window and now - window[0] > 60:
            window.popleft()

        if len(window) >= self._per_minute:
            raise TooManyAttemptsError

        window.append(now)


class SessionService:
    def __init__(
        self,
        geea: GeeaClient,
        verifier: TokenVerifier,
        mapping: AreaMapping,
        client: str,
        limiter: AttemptLimiter,
    ):
        self._geea = geea
        self._verifier = verifier
        self._mapping = mapping
        self._client = client
        self._limiter = limiter

    async def login(self, username: str, password: str, client_ip: str) -> Session:
        self._limiter.check(username.strip().lower())
        output = await self._geea.login(username, password, client_ip)
        return await self._session_from(output)

    async def refresh(self, refresh_token: str) -> Session:
        output = await self._geea.refresh(refresh_token)
        return await self._session_from(output)

    async def _session_from(self, output: dict[str, Any]) -> Session:
        access_token = str(output.get("accessToken") or "")

        # As claims que vêm ao lado do token não estão assinadas: valida-se o JWT.
        try:
            claims = await self._verifier.verify(access_token)
        except AuthError as exc:
            raise InvalidCredentialsError from exc

        principal = build_principal(claims, self._mapping, self._client)

        # Mesmo erro das credenciais inválidas: não confirma que a conta existe.
        if not principal.areas and not principal.service_access:
            raise InvalidCredentialsError

        return Session(
            principal=principal,
            access_token=access_token,
            refresh_token=str(output.get("refreshToken") or ""),
            expires_in=_as_int(output.get("expiresIn")),
        )


def _as_int(value: object) -> int:
    """O GEEA devolve `expiresIn` como string («18000»), não como número."""
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0
