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

from app.controllers.dependencies import get_case_service, get_validation_service
from app.domain.errors import InvalidCaseStatusError, NotFoundError, NothingToUpdateError
from app.infrastructure.auth import auth
from app.infrastructure.tables import ClosingDetail, CreditMovement, Execution, PendingCase
from app.main import app
from mozaops_libs.auth import Principal

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
        executed_at=datetime(2026, 9, 2, 3, 15, 10),
        period_start=date(2026, 6, 21),
        period_end=date(2026, 6, 28),
        report_name="FECHO_POS_DOP 21 a 28 de Junho-2026",
        pos_list_file="pos-list.xlsx",
        simo_closings_file="simo-closings.xlsx",
        banka_credits_file="banka-credits.xlsx",
        summary=dict(SUMMARY),
    )


def make_detail() -> ClosingDetail:
    return ClosingDetail(
        id="d1",
        execution_id=EXECUTION_ID,
        pos_id="259342",
        merchant="Comerciante de teste",
        account_number="000123456789",
        period=209,
        key=KEY,
        simo_closing_date=date(2026, 6, 23),
        operation_number=7,
        simo_closing_total=Decimal("1000.00"),
        simo_key_total=Decimal("1000.00"),
        closing_description="P24-Fecho TPA 0000259342 - 209",
        banka_credit_date=date(2026, 6, 24),
        banka_closing_total=Decimal("7641.00"),
        closing_type="D_PLUS_1",
        validation="mismatch",
        difference=Decimal("6641.00"),
    )


def make_case() -> PendingCase:
    return PendingCase(
        id=CASE_ID,
        execution_id=EXECUTION_ID,
        key=KEY,
        pos_id="259342",
        period=209,
        merchant="Comerciante de teste",
        account_number="000123456789",
        simo_amount=Decimal("1000.00"),
        banka_amount=Decimal("7641.00"),
        type="mismatch",
        e_ticket=None,
        status="pending",
        resolved_at=None,
    )


def make_movement() -> CreditMovement:
    return CreditMovement(
        id="m1",
        execution_id=EXECUTION_ID,
        key=KEY,
        movement_date=date(2026, 6, 24),
        amount=Decimal("7641.00"),
        description="P24-Fecho TPA 0000259342 - 209",
    )


class FakeService:
    """Faz de `ValidationService` e de `CaseService` ao mesmo tempo.

    Um objecto só para os dois porque partilham estado: mudar um caso e reler a
    execução a seguir tem de ver a mesma coisa, como veria em produção.

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

    async def run(self, files: Any) -> str:
        self.chamadas["run_validation"] = {slot: nome for slot, (_, nome) in files.items()}
        return EXECUTION_ID

    async def get_execution(self, execution_id: str) -> Execution:
        return self._guard(execution_id)

    async def get_latest_execution(self) -> Execution | None:
        return self.execution

    async def list_cases(self, _execution_id: str) -> list[PendingCase]:
        return self.cases

    async def list_details(
        self, execution_id: str, page: Any, validation: Any, search: Any
    ) -> tuple[list[ClosingDetail], int, dict[str, int]]:
        self.chamadas["list_details"] = {
            "page": page.page,
            # A chave é o nome do PARÂMETRO da query, não o do campo Python:
            # é isso que o teste afirma, e é isso que o SPA envia.
            "perPage": page.per_page,
            "validation": validation,
            "search": search,
        }
        self._guard(execution_id)
        return self.details, len(self.details), self.counts

    async def get_key_breakdown(self, execution_id: str, key: str) -> dict[str, Any]:
        self._guard(execution_id)
        if key != KEY:
            raise NotFoundError("Não há nenhum fecho com esta chave nesta execução.")
        return {
            "key": key,
            "closings": self.details,
            "movements": self.movements,
            "case": self.cases[0],
        }

    async def update(
        self, case_id: str, patch: dict[str, Any]
    ) -> tuple[PendingCase, dict[str, Any]]:
        self.chamadas["update_case"] = patch
        if case_id != CASE_ID:
            raise NotFoundError("O caso indicado não existe.")
        if not patch:
            raise NothingToUpdateError(
                "O pedido não indica nada para alterar. Envie o estado, o e-Ticket, ou ambos."
            )
        if "status" in patch and patch["status"] not in ("pending", "in-review", "resolved"):
            raise InvalidCaseStatusError(
                f"Estado de caso inválido: «{patch['status']}». "
                "Os estados possíveis são «pending», «in-review» e «resolved»."
            )

        caso = self.cases[0]
        if "e_ticket" in patch:
            caso.e_ticket = patch["e_ticket"]
        if "status" in patch:
            caso.status = {"in-review": "in_review"}.get(patch["status"], patch["status"])
        return caso, dict(SUMMARY)

    async def build_report(self, execution_id: str) -> tuple[bytes, str]:
        execucao = self._guard(execution_id)
        return b"PK\x03\x04conteudo-xlsx", f"{execucao.report_name}.xlsx"


@pytest.fixture
def service() -> FakeService:
    return FakeService()


DA_AREA = Principal(
    subject="6961d9f6-5529-457b-93cb-db82230a00cb",
    username="m001926",
    name="Operador de teste",
    email="operador.teste@mozabanco.co.mz",
    areas=frozenset({"channels"}),
    department_code="3230",
    department="Canais e Serviços de Integração",
    function="Director",
    employee_id="1926",
)


@pytest.fixture
def client(service: FakeService) -> Any:
    """Cliente HTTP contra a app real, com os dois serviços substituídos.

    A substituição é feita na fronteira que o `dependencies.py` declara, e é aí
    que ela pára: nada abaixo — repositório, sessão, engine — chega a existir.

    A autenticação é substituída **só na leitura do token** — quem está do
    outro lado — e não na guarda de área: essa continua a correr a sério,
    contra alguém da área. Substituí-la apagaria a verificação que se quer
    testada. Quem prova que as rotas estão fechadas é o `test_auth.py`, que não
    substitui nada disto.
    """
    app.dependency_overrides[get_validation_service] = lambda: service
    app.dependency_overrides[get_case_service] = lambda: service
    app.dependency_overrides[auth.principal] = lambda: DA_AREA
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
