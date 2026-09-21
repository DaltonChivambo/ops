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

from app.controllers.dependencies import (
    get_case_service,
    get_settings_service,
    get_validation_service,
)
from app.domain.e_ticket import normalize_e_ticket
from app.domain.errors import (
    InvalidCaseStatusError,
    InvalidMatchError,
    NotFoundError,
    NothingToUpdateError,
)
from app.domain.matching import (
    Match,
    MatchEffect,
    is_fully_matched,
    suggest_matches,
    validate_matches,
)
from app.domain.sla import DEFAULT_SLA_DAYS, DEFAULT_WARNING_DAYS, validate_sla
from app.infrastructure.auth import auth
from app.infrastructure.tables import ClosingDetail, CreditMovement, Execution, PendingCase
from app.main import app
from app.services.case_service import STATUS_FROM_JSON, ReconciledCase
from app.services.match_sides import closing_side, movement_side
from app.services.settings_service import SlaSettings
from app.services.validation_service import DetailsPage, ReconciliationCandidate
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
        first_date=date(2026, 6, 23),
        first_date_source="simo",
        status_since=date(2026, 6, 30),
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

    Guarda o que lhe pediram (`calls`), para os testes poderem afirmar que a
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
            "simo_duplicates": 0,
        }
        # (nº fechos SIMO, nº movimentos Banka) por chave — só preenchido pelos
        # testes que precisam de simular uma chave `duplicated`. Vazio por
        # omissão: a fixture por omissão é `mismatch`, não pede contagem nenhuma.
        self.key_counts: dict[str, tuple[int, int]] = {}
        # (nº, montante) dos créditos sem fecho por chave — vazio por omissão.
        self.matches: list[Match] = []
        self.calls: dict[str, Any] = {}

    def _guard(self, execution_id: str) -> Execution:
        if self.execution is None or execution_id != self.execution.id:
            raise NotFoundError("A execução indicada não existe ou já foi removida.")
        return self.execution

    async def run(self, files: Any) -> str:
        self.calls["run_validation"] = {slot: name for slot, (_, name) in files.items()}
        return EXECUTION_ID

    async def get_execution(self, execution_id: str) -> Execution:
        return self._guard(execution_id)

    async def get_latest_execution(self) -> Execution | None:
        return self.execution

    async def set_count_simo_duplicates(self, execution_id: str, counted: bool) -> dict[str, Any]:
        self.calls["set_count_simo_duplicates"] = {"counted": counted}
        execution = self._guard(execution_id)
        execution.count_simo_duplicates = counted
        summary = {**(execution.summary or {}), "countSimoDuplicates": counted}
        execution.summary = summary
        return summary

    async def list_cases(
        self, _execution_id: str
    ) -> tuple[list[PendingCase], dict[str, tuple[int, int]]]:
        return self.cases, self.key_counts

    async def list_details(
        self,
        execution_id: str,
        page: Any,
        validation: Any,
        search: Any,
        repeated: Any = "all",
    ) -> DetailsPage:
        self.calls["list_details"] = {
            "page": page.page,
            # A chave é o nome do PARÂMETRO da query, não o do campo Python:
            # é isso que o teste afirma, e é isso que o SPA envia.
            "perPage": page.per_page,
            "validation": validation,
            "search": search,
            "repeated": str(repeated),
        }
        self._guard(execution_id)
        return DetailsPage(
            details=self.details,
            total=len(self.details),
            counts=self.counts,
            key_counts=self.key_counts,
        )

    async def get_key_breakdown(self, execution_id: str, key: str) -> dict[str, Any]:
        self._guard(execution_id)
        if key != KEY:
            raise NotFoundError("Não há nenhum fecho com esta chave nesta execução.")
        return {
            "key": key,
            "closings": self.details,
            "movements": self.movements,
            "case": self.cases[0],
            "matches": self.matches,
            "suggested_matches": suggest_matches(
                [closing_side(row) for row in self.details],
                [movement_side(row) for row in self.movements],
            ),
        }

    async def list_reconciliation_candidates(
        self, execution_id: str
    ) -> list[ReconciliationCandidate]:
        self._guard(execution_id)
        case = self.cases[0]
        if case.type != "duplicated" or case.status == "resolved" or self.matches:
            return []
        # A regra é a do serviço a sério: só entra a chave em que todos os fechos
        # têm um crédito do mesmo valor.
        closings = [closing_side(row) for row in self.details]
        suggested = suggest_matches(closings, [movement_side(row) for row in self.movements])
        if not is_fully_matched(suggested, closings):
            return []
        return [
            ReconciliationCandidate(
                case=case,
                closings=self.details,
                movements=self.movements,
                matches=[],
                suggested_matches=suggested,
            )
        ]

    async def reconcile(
        self, case_id: str, matches: list[Match], matched_by: str | None
    ) -> tuple[ReconciledCase, dict[str, Any]]:
        self.calls["reconcile"] = {
            "matches": [(match.closing_id, match.movement_id) for match in matches],
            "matched_by": matched_by,
        }
        return self._apply_matches(case_id, matches), dict(SUMMARY)

    async def reconcile_many(
        self,
        execution_id: str,
        requests: list[tuple[str, list[Match]]],
        matched_by: str | None,
    ) -> tuple[list[ReconciledCase], dict[str, Any]]:
        self.calls["reconcile_many"] = {
            "case_ids": [case_id for case_id, _ in requests],
            "matched_by": matched_by,
        }
        self._guard(execution_id)
        if not requests:
            raise NothingToUpdateError("O pedido não traz nenhum caso para conciliar.")
        return [self._apply_matches(case_id, matches) for case_id, matches in requests], dict(
            SUMMARY
        )

    def _apply_matches(self, case_id: str, matches: list[Match]) -> ReconciledCase:
        if case_id != CASE_ID:
            raise NotFoundError("O caso indicado não existe.")
        case = self.cases[0]
        if case.type != "duplicated":
            raise InvalidMatchError("Só os casos de períodos repetidos se conciliam fecho a fecho.")

        # As regras são as do domínio, como no serviço a sério: é ali que nasce
        # a mensagem em português que a rota tem de fazer chegar ao operador.
        closings = [closing_side(row) for row in self.details]
        movements = [movement_side(row) for row in self.movements]
        validate_matches(matches, closings, movements)
        self.matches = list(matches)
        if is_fully_matched(matches, closings):
            case.status = "resolved"
            case.status_since = date(2026, 9, 10)
            case.resolved_at = date(2026, 9, 10)
        nothing = MatchEffect(0, Decimal(0), Decimal(0))
        return ReconciledCase(
            case=case,
            counts=(len(self.details), len(self.movements)),
            # O serviço a sério devolve as linhas gravadas; o que a rota lê delas
            # (`closing_id`, `movement_id`) é igual num `Match`.
            matches=self.matches,
            before=nothing,
            after=nothing,
        )

    async def update(
        self, case_id: str, patch: dict[str, Any]
    ) -> tuple[PendingCase, dict[str, Any], tuple[int, int]]:
        self.calls["update_case"] = patch
        if case_id != CASE_ID:
            raise NotFoundError("O caso indicado não existe.")
        if not patch:
            raise NothingToUpdateError(
                "O pedido não indica nada para alterar. Envie o estado, o e-Ticket, ou ambos."
            )
        if "status" in patch and patch["status"] not in STATUS_FROM_JSON:
            raise InvalidCaseStatusError(
                f"Estado de caso inválido: «{patch['status']}». "
                f"Os estados possíveis são «{'», «'.join(STATUS_FROM_JSON)}»."
            )

        # Valida antes de mexer no caso, como o serviço a sério: um e-Ticket
        # recusado não pode deixar o estado já mudado. A função é a do domínio —
        # a mensagem em português que chega ao operador nasce ali.
        e_ticket = normalize_e_ticket(patch["e_ticket"]) if "e_ticket" in patch else None

        case = self.cases[0]
        if "e_ticket" in patch:
            case.e_ticket = e_ticket
        if "status" in patch:
            case.status = STATUS_FROM_JSON[patch["status"]]
            case.status_since = date(2026, 9, 10)
        return case, dict(SUMMARY), self.key_counts.get(case.key, (1, 1))

    async def build_report(self, execution_id: str) -> tuple[bytes, str]:
        execution = self._guard(execution_id)
        return b"PK\x03\x04conteudo-xlsx", f"{execution.report_name}.xlsx"


class FakeSettingsService:
    """Faz de `SettingsService` — guarda o prazo em memória.

    Valida com a mesma função do domínio que o serviço a sério usa: o que se
    quer testar na rota é que a mensagem em português chega ao operador, e ela
    nasce ali.
    """

    def __init__(self) -> None:
        self.sla = SlaSettings(
            case_sla_days=DEFAULT_SLA_DAYS,
            case_warning_days=DEFAULT_WARNING_DAYS,
            updated_at=None,
            updated_by=None,
        )

    async def get(self) -> SlaSettings:
        return self.sla

    async def save(self, sla_days: int, warning_days: int, updated_by: str | None) -> SlaSettings:
        validate_sla(sla_days, warning_days)
        self.sla = SlaSettings(
            case_sla_days=sla_days,
            case_warning_days=warning_days,
            updated_at=datetime(2026, 9, 10, 8, 30),
            updated_by=updated_by,
        )
        return self.sla


@pytest.fixture
def service() -> FakeService:
    return FakeService()


@pytest.fixture
def settings_service() -> FakeSettingsService:
    return FakeSettingsService()


AREA_MEMBER = Principal(
    subject="6961d9f6-5529-457b-93cb-db82230a00cb",
    username="m001926",
    name="Operador de teste",
    email="operador.teste@mozabanco.co.mz",
    areas=frozenset({"channels"}),
    service_access={},
    department_code="3230",
    department="Canais e Serviços de Integração",
    function="Director",
    employee_id="1926",
)


@pytest.fixture
def client(service: FakeService, settings_service: FakeSettingsService) -> Any:
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
    app.dependency_overrides[get_settings_service] = lambda: settings_service
    app.dependency_overrides[auth.principal] = lambda: AREA_MEMBER
    with TestClient(app) as http_client:
        yield http_client
    app.dependency_overrides.clear()


@pytest.fixture
def files() -> dict[str, tuple[str, bytes, str]]:
    """Os três campos multipart. O conteúdo é irrelevante: ninguém o abre."""
    xlsx = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return {
        "posList": ("pos-list.xlsx", b"conteudo", xlsx),
        "simoClosings": ("simo-closings.xlsx", b"conteudo", xlsx),
        "bankaCredits": ("banka-credits.xlsx", b"conteudo", xlsx),
    }
