"""Paginação — porte de `shared/pagination.py` do MozaOps v1.

Converte os query params (`page`, `perPage`) em `skip`/`take`.
"""
from dataclasses import dataclass

DEFAULT_PER_PAGE = 50
MAX_PER_PAGE = 200


@dataclass(slots=True)
class Page:
    page: int
    perPage: int

    @property
    def skip(self) -> int:
        return (self.page - 1) * self.perPage

    @property
    def take(self) -> int:
        return self.perPage


def parse_page(page: int | None, per_page: int | None) -> Page:
    return Page(
        page=max(1, page or 1),
        perPage=min(MAX_PER_PAGE, max(1, per_page or DEFAULT_PER_PAGE)),
    )
