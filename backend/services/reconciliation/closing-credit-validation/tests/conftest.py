"""Andaime dos testes de rota: um cliente HTTP com a camada de serviço falsa.

**Toda** a falsificação vive aqui, de propósito. Os testes em `test_api.py`
afirmam apenas coisas sobre o HTTP — estado, corpo, cabeçalhos — que é o
contrato que o frontend consome e a única coisa que não pode mudar. Quando as
camadas mudarem de sítio, é este ficheiro que se reescreve; os testes ficam
como estão, e é isso que os torna prova de que a mudança não partiu nada.

Sem base de dados e sem `.xlsx`: correm no `make test` de hoje, em qualquer
máquina, sem preparar nada.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import routes
from app.database import get_session
from app.errors import NotFoundError
from app.main import app
from app.models import ClosingDetail, CreditMovement, Execution, PendingCase

EXECUTION_ID = "3f2b1c00-0000-4000-8000-000000000001"
CASE_ID = "3f2b1c00-0000-4000-8000-000000000002"
KEY = "259342209"

# O `summary` é guardado em JSONB e servido em bruto ao frontend, por isso as
# chaves são as do `models.ts` e não as do Python. Aqui está o subconjunto que
# chega para os testes; o `test_contract` é que confere a lista completa.
SUMMARY: dict[str, Any] = {
    "processed": 18138,
    "matched": 18003,
    "divergent": 119,
    "validationRate": 99.3,
    "divergenceAmount": 1027205.32,
    "openCases": 119,
    "resolvedCases": 0,
    "missingCount": 118,
    "mismatchCount": 1,
}


def make_execution() -> Execution:
    return Execution(
        id=EXECUTION_ID,
        executedAt=datetime(2026, 9, 2, 3, 15, 10),
        periodStart=date(2026, 6, 21),
        periodEnd=date(2026, 6, 28),
        reportName="FECHO_POS_DOP 21 a 28 de Junho-2026",
        posListFile="pos-list.xlsx",
        simoClosingsFile="simo-closings.xlsx",
        bankaCreditsFile="banka-credits.xlsx",
        summary=dict(SUMMARY),
    )


def make_detail() -> ClosingDetail:
    return ClosingDetail(
        id="d1",
        executionId=EXECUTION_ID,
        posId="259342",
        merchant="Comerciante de teste",
        accountNumber="000123456789",
        period=209,
        key=KEY,
        simoClosingDate=date(2026, 6, 23),
        operationNumber=7,
        simoClosingTotal=Decimal("1000.00"),
        simoKeyTotal=Decimal("1000.00"),
        closingDescription="P24-Fecho TPA 0000259342 - 209",
        bankaCreditDate=date(2026, 6, 24),
        bankaClosingTotal=Decimal("7641.00"),
        closingType="D_PLUS_1",
        validation="mismatch",
        difference=Decimal("6641.00"),
    )


def make_case() -> PendingCase:
    return PendingCase(
        id=CASE_ID,
        executionId=EXECUTION_ID,
        key=KEY,
        posId="259342",
        period=209,
        merchant="Comerciante de teste",
        accountNumber="000123456789",
        simoAmount=Decimal("1000.00"),
        bankaAmount=Decimal("7641.00"),
        type="mismatch",
        eTicket=None,
        status="pending",
        resolvedAt=None,
    )


def make_movement() -> CreditMovement:
    return CreditMovement(
        id="m1",
        executionId=EXECUTION_ID,
        key=KEY,
        movementDate=date(2026, 6, 24),
        amount=Decimal("7641.00"),
        description="P24-Fecho TPA 0000259342 - 209",
    )


class FakeService:
    """Substitui o módulo `service` — as rotas chamam-lhe exactamente o mesmo.

    Guarda o que lhe pediram (`chamadas`), para os testes poderem afirmar que a
    rota encaminhou os argumentos certos sem espreitar para dentro da camada.
    """

    def __init__(self) -> None:
        self.execution: Execution | None = make_execution()
        self.details = [make_detail()]
        self.cases = [make_case()]
        self.movements = [make_movement()]
        self.counts = {
            "all": 1,
            "match": 0,
            "mismatch": 1,
            "missing": 0,
            "zero": 0,
            "duplicated": 0,
        }
        self.chamadas: dict[str, Any] = {}

    def _guard(self, execution_id: str) -> Execution:
        if self.execution is None or execution_id != self.execution.id:
            raise NotFoundError("A execução indicada não existe ou já foi removida.")
        return self.execution

    async def run_validation(self, _session: Any, files: Any) -> str:
        self.chamadas["run_validation"] = {slot: nome for slot, (_, nome) in files.items()}
        return EXECUTION_ID

    async def get_execution(self, _session: Any, execution_id: str) -> Execution:
        return self._guard(execution_id)

    async def get_latest_execution(self, _session: Any) -> Execution | None:
        return self.execution

    async def list_cases(self, _session: Any, _execution_id: str) -> list[PendingCase]:
        return self.cases

    async def list_details(
        self, _session: Any, execution_id: str, page: Any, validation: Any, search: Any
    ) -> tuple[list[ClosingDetail], int, dict[str, int]]:
        self.chamadas["list_details"] = {
            "page": page.page,
            "perPage": page.perPage,
            "validation": validation,
            "search": search,
        }
        self._guard(execution_id)
        return self.details, len(self.details), self.counts

    async def get_key_breakdown(self, _session: Any, execution_id: str, key: str) -> dict[str, Any]:
        self._guard(execution_id)
        if key != KEY:
            raise NotFoundError("Não há nenhum fecho com esta chave nesta execução.")
        return {
            "key": key,
            "closings": self.details,
            "movements": self.movements,
            "case": self.cases[0],
        }

    async def update_case(
        self, _session: Any, case_id: str, patch: dict[str, Any]
    ) -> tuple[PendingCase, dict[str, Any]]:
        self.chamadas["update_case"] = patch
        if case_id != CASE_ID:
            raise NotFoundError("O caso indicado não existe.")
        if not patch:
            raise NotFoundError("Nada a actualizar no caso indicado.")
        if "status" in patch and patch["status"] not in ("pending", "in-review", "resolved"):
            raise NotFoundError("Estado de caso inválido.")

        caso = self.cases[0]
        if "eTicket" in patch:
            caso.eTicket = patch["eTicket"]
        if "status" in patch:
            caso.status = {"in-review": "in_review"}.get(patch["status"], patch["status"])
        return caso, dict(SUMMARY)

    async def build_report(self, _session: Any, execution_id: str) -> tuple[bytes, str]:
        execucao = self._guard(execution_id)
        return b"PK\x03\x04conteudo-xlsx", f"{execucao.reportName}.xlsx"


@pytest.fixture
def service() -> FakeService:
    return FakeService()


@pytest.fixture
def client(service: FakeService, monkeypatch: pytest.MonkeyPatch) -> Any:
    """Cliente HTTP contra a app real, com a camada de serviço substituída.

    O `get_session` é anulado porque a sessão nunca chega a ser usada — quem a
    receberia é o serviço, e esse é falso.
    """
    monkeypatch.setattr(routes, "service", service)
    app.dependency_overrides[get_session] = lambda: None
    with TestClient(app) as cliente:
        yield cliente
    app.dependency_overrides.clear()


@pytest.fixture
def ficheiros() -> dict[str, tuple[str, bytes, str]]:
    """Os três campos multipart. O conteúdo é irrelevante: ninguém o abre."""
    xlsx = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return {
        "posList": ("pos-list.xlsx", b"conteudo", xlsx),
        "simoClosings": ("simo-closings.xlsx", b"conteudo", xlsx),
        "bankaCredits": ("banka-credits.xlsx", b"conteudo", xlsx),
    }
