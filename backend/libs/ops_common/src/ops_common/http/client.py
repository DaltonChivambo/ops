"""Cliente HTTP para chamadas entre serviços — sempre via OSB, nunca direto ao contentor.

Propaga o X-Request-ID; sem isso o rasto no Graylog parte-se na primeira chamada entre serviços.

Aviso de arquitetura: **não usar no caminho de leitura**. Um serviço que precise dos dados de
outro a cada leitura guarda um snapshot actualizado por evento (regra 1, secção 3). Este cliente
é para os casos legítimos de leitura pontual — validar algo na altura de escrever, por exemplo.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from ops_common.logging.correlation import HEADER, get_correlation_id

logger = logging.getLogger(__name__)


class ServicoIndisponivel(Exception):
    """O serviço destino não respondeu, ou respondeu 5xx."""


class ServiceClient:
    def __init__(
        self,
        base_url: str,
        service_name: str,
        timeout: float = 5.0,
        token_provider=None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.service_name = service_name
        self.timeout = timeout
        self.token_provider = token_provider
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)
        return self._client

    async def close(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()

    def _headers(self, extra: dict | None = None) -> dict[str, str]:
        headers = {HEADER: get_correlation_id(), "X-Origin-Service": self.service_name}
        if self.token_provider is not None:
            headers["Authorization"] = f"Bearer {self.token_provider()}"
        if extra:
            headers.update(extra)
        return headers

    async def get(self, path: str, **kwargs: Any) -> httpx.Response:
        return await self._request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> httpx.Response:
        return await self._request("POST", path, **kwargs)

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        client = await self._get_client()
        headers = self._headers(kwargs.pop("headers", None))
        try:
            response = await client.request(method, path, headers=headers, **kwargs)
        except httpx.RequestError as exc:
            logger.warning("Falha a contactar %s%s: %s", self.base_url, path, exc)
            raise ServicoIndisponivel(f"{self.base_url}{path}") from exc
        if response.status_code >= 500:
            raise ServicoIndisponivel(f"{self.base_url}{path} devolveu {response.status_code}")
        return response
