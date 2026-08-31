"""Contrato do token. É plumbing, não domínio: nenhum serviço estende isto com regras suas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CurrentUser(BaseModel):
    """Utilizador autenticado, tal como vem no JWT emitido pelo Auth Service."""

    id: str = Field(alias="sub")
    username: str = ""
    email: str | None = None
    roles: list[str] = []
    permissions: list[str] = []
    department: str | None = None

    model_config = {"populate_by_name": True}

    def has_role(self, *roles: str) -> bool:
        return any(role in self.roles for role in roles)

    def has_permission(self, *permissions: str) -> bool:
        return any(p in self.permissions for p in permissions)
