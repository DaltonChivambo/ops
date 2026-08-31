"""/health e /ready — fora do /api/v1.

São para o healthcheck do Docker e para o OSB; não versionam com a API de negócio.
  /health  processo vivo (nunca consulta dependências)
  /ready   apto a servir (falha com o Postgres em baixo, recupera quando ele voltar)
"""

from __future__ import annotations

from fastapi import APIRouter, Response, status

from reporting.core.config import get_settings
from reporting.infrastructure.persistence.session import verificar_ligacao

router = APIRouter(tags=["operação"])
settings = get_settings()


@router.get("/health", include_in_schema=False)
async def health() -> dict:
    return {"estado": "vivo", "servico": settings.service_name}


@router.get("/ready", include_in_schema=False)
async def ready(response: Response) -> dict:
    base_de_dados = await verificar_ligacao()
    if not base_de_dados:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "estado": "pronto" if base_de_dados else "indisponivel",
        "dependencias": {"base_de_dados": base_de_dados},
    }
