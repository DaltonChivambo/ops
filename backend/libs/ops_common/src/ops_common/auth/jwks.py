"""Verificação local do JWT contra o JWKS do Auth Service.

O OSB roteia e faz o corte grosso, mas não é o único ponto de verificação: sem isto, qualquer
acesso lateral dentro da rede Docker passaria sem controlo (secção 6 do ARCHITECTURE.md).
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

import httpx
import jwt
from jwt import PyJWKSet

logger = logging.getLogger(__name__)


class TokenInvalido(Exception):
    """O token não é verificável: assinatura, expiração, issuer ou audience."""


class JwksClient:
    """Cliente JWKS com cache em memória e refresh por `kid` desconhecido.

    O refresh forçado ao encontrar um `kid` novo é o que permite ao Auth rodar a chave sem
    que os outros serviços tenham de reiniciar.
    """

    def __init__(self, jwks_url: str, cache_ttl: int = 600, timeout: float = 5.0) -> None:
        self.jwks_url = jwks_url
        self.cache_ttl = cache_ttl
        self.timeout = timeout
        self._keys: dict[str, Any] = {}
        self._fetched_at: float = 0.0
        self._lock = threading.Lock()

    def _fetch(self) -> None:
        response = httpx.get(self.jwks_url, timeout=self.timeout)
        response.raise_for_status()
        jwk_set = PyJWKSet.from_dict(response.json())
        self._keys = {key.key_id: key.key for key in jwk_set.keys if key.key_id}
        self._fetched_at = time.monotonic()
        logger.info("JWKS actualizado: %d chave(s)", len(self._keys), extra={"kids": list(self._keys)})

    def get_key(self, kid: str) -> Any:
        with self._lock:
            expirado = (time.monotonic() - self._fetched_at) > self.cache_ttl
            if not self._keys or expirado:
                self._fetch()
            if kid not in self._keys:
                # kid novo: pode ser rotação de chave. Uma segunda tentativa, e só depois falha.
                self._fetch()
            key = self._keys.get(kid)
        if key is None:
            raise TokenInvalido(f"kid desconhecido no JWKS: {kid}")
        return key

    def invalidate(self) -> None:
        with self._lock:
            self._keys = {}
            self._fetched_at = 0.0


def decode_token(
    token: str,
    jwks_client: JwksClient,
    issuer: str,
    audience: str,
    algorithms: list[str] | None = None,
) -> dict[str, Any]:
    """Devolve as claims do token ou levanta `TokenInvalido`."""
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise TokenInvalido("cabeçalho do token ilegível") from exc

    kid = header.get("kid")
    if not kid:
        raise TokenInvalido("token sem kid")

    key = jwks_client.get_key(kid)
    try:
        return jwt.decode(
            token,
            key=key,
            algorithms=algorithms or ["RS256"],
            issuer=issuer,
            audience=audience,
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenInvalido("token expirado") from exc
    except jwt.PyJWTError as exc:
        raise TokenInvalido(str(exc)) from exc
