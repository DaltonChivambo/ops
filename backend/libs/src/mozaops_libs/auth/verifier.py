"""Validação de tokens do GEEA, pelo JWKS.

Assinatura RS256 verificada com a chave pública que o emissor publica — nunca
com um segredo partilhado. É o que permite ao MozaOps aceitar tokens sem
guardar nada do GEEA e sem lhe telefonar a cada pedido.

Duas decisões que não são óbvias:

- **`aud` não é verificado.** Os tokens do GEEA trazem `aud: "account"`, que é
  o que o Keycloak põe quando o cliente não pede audiência nenhuma — não diz
  nada sobre para quem o token serve. Em vez disso verifica-se o `azp`, que
  identifica o cliente que o pediu, contra uma lista fechada.
- **O refrescamento do JWKS é limitado no tempo.** Um `kid` desconhecido faz
  ir buscar as chaves outra vez (é assim que a rotação de chaves funciona sem
  reinícios), mas sem limite isso seria um pedido de saída por cada token
  inventado que chegasse — um amplificador à distância de qualquer um.
"""

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
import jwt

from mozaops_libs.auth.errors import IdentityUnavailableError, UnauthenticatedError

JwksFetcher = Callable[[], Awaitable[dict[str, Any]]]


class TokenVerifier:
    def __init__(
        self,
        *,
        jwks_url: str,
        issuer: str,
        allowed_azp: frozenset[str],
        fetcher: JwksFetcher | None = None,
        cache_seconds: float = 300.0,
        min_refresh_seconds: float = 30.0,
    ):
        self._jwks_url = jwks_url
        self._issuer = issuer
        self._allowed_azp = allowed_azp
        self._fetch = fetcher or self._fetch_over_http
        self._cache_seconds = cache_seconds
        self._min_refresh_seconds = min_refresh_seconds

        self._keys: dict[str, Any] = {}
        self._fetched_at: float = 0.0
        self._lock = asyncio.Lock()

    async def _fetch_over_http(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(self._jwks_url)
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
            return payload

    async def _refresh(self) -> None:
        try:
            document = await self._fetch()
            jwk_set = jwt.PyJWKSet.from_dict(document)
        except (httpx.HTTPError, jwt.PyJWTError, ValueError, KeyError) as exc:
            raise IdentityUnavailableError from exc

        self._keys = {key.key_id: key.key for key in jwk_set.keys if key.key_id}
        self._fetched_at = time.monotonic()

    async def _key_for(self, kid: str) -> Any:
        age = time.monotonic() - self._fetched_at
        if kid in self._keys and age < self._cache_seconds:
            return self._keys[kid]

        async with self._lock:
            # Outra corrotina pode ter refrescado enquanto se esperava.
            if kid in self._keys and time.monotonic() - self._fetched_at < self._cache_seconds:
                return self._keys[kid]

            if time.monotonic() - self._fetched_at < self._min_refresh_seconds and self._keys:
                raise UnauthenticatedError

            await self._refresh()

        key = self._keys.get(kid)
        if key is None:
            raise UnauthenticatedError
        return key

    async def verify(self, token: str) -> dict[str, Any]:
        """Devolve as claims de um token em que se pode confiar."""
        try:
            kid = jwt.get_unverified_header(token).get("kid")
        except jwt.PyJWTError as exc:
            raise UnauthenticatedError from exc

        if not kid:
            raise UnauthenticatedError

        key = await self._key_for(kid)

        try:
            claims: dict[str, Any] = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                issuer=self._issuer,
                options={"verify_aud": False, "require": ["exp", "iat", "sub"]},
            )
        except jwt.PyJWTError as exc:
            raise UnauthenticatedError from exc

        if self._allowed_azp and claims.get("azp") not in self._allowed_azp:
            raise UnauthenticatedError

        return claims
