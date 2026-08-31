"""Camada de aplicação — orquestra o caso de uso.

Porte de `services.py` do MozaOps v1. O pipeline está deliberadamente separado
em `parse → reconcile → persist`: hoje corre síncrono dentro do pedido HTTP
(ver `docs/implementation-plan.md` para o desenho assíncrono futuro), mas a
separação já deixa a porta aberta para isso sem tocar no pipeline em si.
"""
from datetime import date
from typing import IO, Any

from sqlalchemy.ext.asyncio import AsyncSession

from . import repository
from .domain.models import ReconciliationResult
from .domain.reconciliation import NoClosingsError, reconcile
from .errors import BusinessError, NotFoundError
from .infra import parsers, report
from .pagination import Page
from .serializers import CASE_STATUS_VALUES, summary_to_dict

SLOTS = ("posList", "simoClosings", "bankaCredits")


async def run_validation(
    session: AsyncSession, files: dict[str, tuple[IO[bytes], str]]
) -> str:
    """Executa a validação e devolve o id da execução persistida.

    `files` mapeia cada campo multipart para `(stream, nome do ficheiro)`.
    """
    result = _parse_and_reconcile(files)
    names = {slot: files[slot][1] for slot in SLOTS}
    return await repository.create_execution(
        session, result, names, summary_to_dict(result.summary)
    )


def _parse_and_reconcile(files: dict[str, tuple[IO[bytes], str]]) -> ReconciliationResult:
    pos_list = parsers.parse_pos_list(*files["posList"])
    closings = parsers.parse_simo_closings(*files["simoClosings"])
    credits = parsers.parse_banka_credits(*files["bankaCredits"])
    try:
        return reconcile(pos_list, closings, credits)
    except NoClosingsError as error:
        # É uma excepção de negócio do PDD (mensagem já em português, pronta a
        # mostrar) — sobe como tal, não como erro interno.
        raise BusinessError(str(error)) from error


async def get_execution(session: AsyncSession, execution_id: str):
    execution = await repository.find_execution(session, execution_id)
    if execution is None:
        raise NotFoundError("A execução indicada não existe ou já foi removida.")
    return execution


async def get_latest_execution(session: AsyncSession):
    return await repository.find_latest_execution(session)


async def list_cases(session: AsyncSession, execution_id: str):
    return await repository.list_cases(session, execution_id)


async def list_details(
    session: AsyncSession,
    execution_id: str,
    page: Page,
    validation: str | None,
    search: str | None,
):
    details, total = await repository.list_details(session, execution_id, page, validation, search)
    counts = await repository.count_details_by_validation(session, execution_id, search)
    return details, total, counts


async def get_key_breakdown(session: AsyncSession, execution_id: str, key: str) -> dict[str, Any]:
    """Os dois lados de uma chave: os fechos da SIMO e os movimentos do Banka.

    A unidade é a CHAVE e não o fecho, porque o crédito do Banka é da chave: um
    fecho isolado não tem crédito próprio de que se possa falar. Clicar num fecho
    abre a chave a que ele pertence.
    """
    await get_execution(session, execution_id)  # 404 se a execução não existir
    details = await repository.list_details_by_key(session, execution_id, key)
    if not details:
        raise NotFoundError("Não há nenhum fecho com esta chave nesta execução.")
    return {
        "key": key,
        "closings": details,
        "movements": await repository.list_movements_by_key(session, execution_id, key),
        "case": await repository.find_case_by_key(session, execution_id, key),
    }


async def update_case(session: AsyncSession, case_id: str, patch: dict[str, Any]):
    """Actualiza estado/e-Ticket de um caso e recalcula o `summary` da execução."""
    data: dict[str, Any] = {}
    if "eTicket" in patch:
        e_ticket = patch["eTicket"]
        data["eTicket"] = e_ticket.strip() if isinstance(e_ticket, str) and e_ticket.strip() else None
    if "status" in patch:
        status = CASE_STATUS_VALUES.get(patch["status"], patch["status"])
        if status not in ("pending", "in_review", "resolved"):
            raise NotFoundError("Estado de caso inválido.")
        data["status"] = status
        data["resolvedAt"] = date.today() if status == "resolved" else None

    if not data:
        raise NotFoundError("Nada a actualizar no caso indicado.")

    case = await repository.update_case(session, case_id, data)
    if case is None:
        raise NotFoundError("O caso indicado não existe.")

    summary = await _refresh_case_counters(session, case.executionId)
    return case, summary


async def _refresh_case_counters(session: AsyncSession, execution_id: str) -> dict[str, Any]:
    """Reflecte no `summary` guardado as contagens de casos abertos/regularizados."""
    execution = await get_execution(session, execution_id)
    summary = dict(execution.summary or {})
    counts = await repository.count_cases_by_status(session, execution_id)
    resolved = counts.get("resolved", 0)
    summary["resolvedCases"] = resolved
    summary["openCases"] = sum(counts.values()) - resolved
    await repository.save_summary(session, execution_id, summary)
    return summary


async def build_report(session: AsyncSession, execution_id: str) -> tuple[bytes, str]:
    """Gera o .xlsx da execução a partir do que está persistido."""
    execution = await get_execution(session, execution_id)
    details = await repository.list_all_details(session, execution_id)
    cases = await repository.list_cases(session, execution_id)
    content = report.build_workbook(execution, details, cases)
    return content, f"{execution.reportName}.xlsx"
