"""Camada de apresentação — modelos SQLAlchemy e domínio → dicts JSON.

Porte de `serializers.py` do MozaOps v1. Chaves em inglês (são consumidas por
código, e espelham `models.ts` do frontend 1:1). Os enums são traduzidos para
os literais que o frontend mostra: `D_PLUS_1` → `'D+1'`, `NA` → `'n.a'`,
`in_review` → `'in-review'`.
"""
from dataclasses import asdict
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from .domain.models import ClosingSummary
from .models import ClosingDetail, CreditMovement, Execution, PendingCase

CLOSING_TYPE_LABELS = {"D": "D", "D_PLUS_1": "D+1", "NA": "n.a"}
CASE_STATUS_LABELS = {"pending": "pending", "in_review": "in-review", "resolved": "resolved"}
CASE_STATUS_VALUES = {value: key for key, value in CASE_STATUS_LABELS.items()}


def summary_to_dict(summary: ClosingSummary) -> dict[str, Any]:
    return {key: _plain(value) for key, value in asdict(summary).items()}


def execution_to_dict(
    execution: Execution,
    cases: list[PendingCase] | None = None,
) -> dict[str, Any]:
    payload = {
        "executionId": execution.id,
        "executedAt": _plain(execution.executedAt),
        "periodStart": _plain(execution.periodStart),
        "periodEnd": _plain(execution.periodEnd),
        "reportName": execution.reportName,
        "files": {
            "posList": execution.posListFile,
            "simoClosings": execution.simoClosingsFile,
            "bankaCredits": execution.bankaCreditsFile,
        },
        "summary": execution.summary,
    }
    if cases is not None:
        payload["cases"] = [case_to_dict(case) for case in cases]
    return payload


def detail_to_dict(detail: ClosingDetail) -> dict[str, Any]:
    return {
        "id": detail.id,
        "posId": detail.posId,
        "merchant": detail.merchant,
        "accountNumber": detail.accountNumber,
        "period": detail.period,
        "key": detail.key,
        "simoClosingDate": _plain(detail.simoClosingDate),
        "operationNumber": detail.operationNumber,
        "simoClosingTotal": _plain(detail.simoClosingTotal),
        "simoKeyTotal": _plain(detail.simoKeyTotal),
        "closingDescription": detail.closingDescription,
        "bankaCreditDate": _plain(detail.bankaCreditDate),
        "bankaClosingTotal": _plain(detail.bankaClosingTotal),
        "closingType": CLOSING_TYPE_LABELS.get(detail.closingType, "n.a"),
        "validation": detail.validation,
        "difference": _plain(detail.difference),
    }


def movement_to_dict(movement: CreditMovement) -> dict[str, Any]:
    return {
        "id": movement.id,
        "key": movement.key,
        "date": _plain(movement.movementDate),
        "amount": _plain(movement.amount),
        "description": movement.description,
    }


def key_breakdown_to_dict(breakdown: dict[str, Any]) -> dict[str, Any]:
    """Os dois lados de uma chave, para o painel de detalhe de um fecho."""
    case = breakdown["case"]
    return {
        "key": breakdown["key"],
        "closings": [detail_to_dict(detail) for detail in breakdown["closings"]],
        "movements": [movement_to_dict(movement) for movement in breakdown["movements"]],
        "case": case_to_dict(case) if case else None,
    }


def case_to_dict(case: PendingCase) -> dict[str, Any]:
    return {
        "id": case.id,
        "key": case.key,
        "posId": case.posId,
        "period": case.period,
        "merchant": case.merchant,
        "accountNumber": case.accountNumber,
        "simoAmount": _plain(case.simoAmount),
        "bankaAmount": _plain(case.bankaAmount),
        "type": case.type,
        "eTicket": case.eTicket,
        "status": CASE_STATUS_LABELS.get(case.status, case.status),
        "resolvedAt": _plain(case.resolvedAt),
    }


def _plain(value: Any) -> Any:
    """Decimal → float, data/hora → ISO. O front formata com `Intl`."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value
