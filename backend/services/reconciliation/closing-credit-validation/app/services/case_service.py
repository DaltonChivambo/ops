"""Caso de uso do caso de divergência: mudar-lhe o estado e o e-Ticket.

Cada alteração obriga a recontar os casos abertos e regularizados, porque esses
dois números vivem dentro do `summary` guardado da execução — é o que o painel
lê sem ter de contar linhas.
"""

from datetime import date
from typing import Any

from app.domain.errors import NotFoundError
from app.domain.vocabulary import CaseStatus
from app.infrastructure.tables import PendingCase
from app.repositories.case_repository import CaseRepository
from app.repositories.execution_repository import ExecutionRepository

# `in-review` é o que viaja no JSON; `in_review` é o valor do enum na base. É a
# única diferença entre os dois lados, e vive aqui em vez de num `if`.
STATUS_FROM_JSON = {
    "pending": CaseStatus.PENDING,
    "in-review": CaseStatus.IN_REVIEW,
    "resolved": CaseStatus.RESOLVED,
}


class CaseService:
    def __init__(self, cases: CaseRepository, executions: ExecutionRepository) -> None:
        self._cases = cases
        self._executions = executions

    async def update(
        self, case_id: str, patch: dict[str, Any]
    ) -> tuple[PendingCase, dict[str, Any]]:
        """Actualiza estado/e-Ticket de um caso e recalcula o `summary` da execução."""
        data: dict[str, Any] = {}
        if "eTicket" in patch:
            e_ticket = patch["eTicket"]
            data["eTicket"] = (
                e_ticket.strip() if isinstance(e_ticket, str) and e_ticket.strip() else None
            )
        if "status" in patch:
            status = STATUS_FROM_JSON.get(patch["status"])
            if status is None:
                raise NotFoundError("Estado de caso inválido.")
            data["status"] = status
            data["resolvedAt"] = date.today() if status is CaseStatus.RESOLVED else None

        if not data:
            raise NotFoundError("Nada a actualizar no caso indicado.")

        case = await self._cases.update(case_id, data)
        if case is None:
            raise NotFoundError("O caso indicado não existe.")

        return case, await self._refresh_counters(case.executionId)

    async def _refresh_counters(self, execution_id: str) -> dict[str, Any]:
        """Reflecte no `summary` guardado as contagens de casos abertos/regularizados."""
        execution = await self._executions.find(execution_id)
        if execution is None:
            raise NotFoundError("A execução indicada não existe ou já foi removida.")

        summary = dict(execution.summary or {})
        counts = await self._cases.count_by_status(execution_id)
        resolved = counts.get(CaseStatus.RESOLVED, 0)
        # Chaves em camelCase de propósito: são as do documento guardado em JSONB,
        # que o frontend lê tal como está — não são atributos de Python.
        summary["resolvedCases"] = resolved
        summary["openCases"] = sum(counts.values()) - resolved
        await self._executions.save_summary(execution_id, summary)
        return summary
