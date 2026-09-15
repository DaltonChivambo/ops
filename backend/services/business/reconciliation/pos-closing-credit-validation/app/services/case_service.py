"""Caso de uso do caso de divergência: mudar-lhe o estado e o e-Ticket.

Cada alteração obriga a recontar os casos abertos e regularizados, porque esses
dois números vivem dentro do `summary` guardado da execução — é o que o painel
lê sem ter de contar linhas.
"""

from datetime import date
from typing import Any

from app.domain.e_ticket import normalize_e_ticket
from app.domain.errors import InvalidCaseStatusError, NotFoundError, NothingToUpdateError
from app.domain.vocabulary import CaseStatus, CaseType
from app.infrastructure.tables import PendingCase
from app.repositories.case_repository import CaseRepository
from app.repositories.execution_repository import ExecutionRepository

# O JSON usa hífens onde o enum usa underscores. É a única diferença entre os
# dois lados, e vive aqui em vez de num `if`.
STATUS_FROM_JSON = {
    "pending": CaseStatus.PENDING,
    "in-review-internal": CaseStatus.IN_REVIEW_INTERNAL,
    "in-review-simo": CaseStatus.IN_REVIEW_SIMO,
    "resolved": CaseStatus.RESOLVED,
}


class CaseService:
    def __init__(self, cases: CaseRepository, executions: ExecutionRepository) -> None:
        self._cases = cases
        self._executions = executions

    async def update(
        self, case_id: str, patch: dict[str, Any]
    ) -> tuple[PendingCase, dict[str, Any], tuple[int, int]]:
        """Actualiza estado/e-Ticket de um caso e recalcula o `summary` da execução."""
        data: dict[str, Any] = {}
        if "e_ticket" in patch:
            data["e_ticket"] = normalize_e_ticket(patch["e_ticket"])
        if "status" in patch:
            status = STATUS_FROM_JSON.get(patch["status"])
            if status is None:
                possiveis = "», «".join(STATUS_FROM_JSON)
                raise InvalidCaseStatusError(
                    f"Estado de caso inválido: «{patch['status']}». "
                    f"Os estados possíveis são «{possiveis}»."
                )
            data["status"] = status
            # O relógio do estado recomeça a cada mudança: é o que responde a
            # «submetido à SIMO há quanto tempo?» e a «e a análise interna?».
            data["status_since"] = date.today()
            data["resolved_at"] = date.today() if status is CaseStatus.RESOLVED else None

        if not data:
            raise NothingToUpdateError(
                "O pedido não indica nada para alterar. Envie o estado, o e-Ticket, ou ambos."
            )

        case = await self._cases.update(case_id, data)
        if case is None:
            raise NotFoundError("O caso indicado não existe.")

        counts = (1, 1)
        if case.type == CaseType.DUPLICATED:
            key_counts = await self._executions.count_by_key(case.execution_id, {case.key})
            counts = key_counts.get(case.key, (1, 1))

        return case, await self._refresh_counters(case.execution_id), counts

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
