"""As contagens pedem-se uma vez por consulta, não uma vez por página.

O `total` e as contagens dos chips valem para a consulta inteira e não mudam de
uma página para a seguinte, mas são as duas leituras que varrem a execução toda.
A tabela pagina por «carregar mais», portanto pedi-las em cada página multiplica
o custo pelo número de páginas.

Afirma-se o que interessa: na segunda página **não se vai ao servidor buscá-las**.
"""

from typing import Any, cast

import pytest

from app.pagination import Page
from app.repositories.case_repository import CaseRepository
from app.repositories.execution_repository import ExecutionRepository
from app.repositories.match_repository import MatchRepository
from app.services.validation_service import ValidationService

COUNTS = {
    "all": 3,
    "simo_duplicates": 0,
    "match": 3,
    "mismatch": 0,
    "missing": 0,
    "zero": 0,
    "duplicated": 0,
}


class SpyExecutions:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def list_details(self, *_args: Any, **_kwargs: Any) -> list[Any]:
        self.calls.append("list_details")
        return []

    async def count_details(self, *_args: Any, **_kwargs: Any) -> int:
        self.calls.append("count_details")
        return 3

    async def count_details_by_validation(self, *_args: Any, **_kwargs: Any) -> dict[str, int]:
        self.calls.append("count_details_by_validation")
        return COUNTS

    async def count_by_key(self, *_args: Any, **_kwargs: Any) -> dict[str, tuple[int, int]]:
        return {}


def _service(executions: SpyExecutions) -> ValidationService:
    return ValidationService(
        cast(ExecutionRepository, executions),
        cast(CaseRepository, None),
        cast(MatchRepository, None),
    )


@pytest.fixture
def executions() -> SpyExecutions:
    return SpyExecutions()


async def test_first_page_brings_the_counts(executions):
    page = await _service(executions).list_details("exec-1", Page(page=1, per_page=50), None, None)

    assert page.total == 3
    assert page.counts == COUNTS
    assert "count_details" in executions.calls
    assert "count_details_by_validation" in executions.calls


async def test_later_pages_do_not_ask_for_them_again(executions):
    page = await _service(executions).list_details("exec-1", Page(page=2, per_page=50), None, None)

    assert page.total is None
    assert page.counts is None
    assert executions.calls == ["list_details"]
