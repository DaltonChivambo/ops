"""Paginação uniforme. O Angular consome sempre a mesma forma, venha de que serviço vier."""

from __future__ import annotations

from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel

T = TypeVar("T")


class ParametrosPagina(BaseModel):
    pagina: int = 1
    tamanho: int = 25

    @property
    def offset(self) -> int:
        return (self.pagina - 1) * self.tamanho

    @property
    def limit(self) -> int:
        return self.tamanho


def parametros_pagina(
    pagina: int = Query(1, ge=1, description="Página, a começar em 1."),
    tamanho: int = Query(25, ge=1, le=200, description="Registos por página."),
) -> ParametrosPagina:
    return ParametrosPagina(pagina=pagina, tamanho=tamanho)


class Pagina(BaseModel, Generic[T]):
    itens: list[T]
    total: int
    pagina: int
    tamanho: int

    @property
    def total_paginas(self) -> int:
        return (self.total + self.tamanho - 1) // self.tamanho if self.tamanho else 0

    @classmethod
    def de(cls, itens: list[T], total: int, params: ParametrosPagina) -> "Pagina[T]":
        return cls(itens=itens, total=total, pagina=params.pagina, tamanho=params.tamanho)
