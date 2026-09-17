"""Os schemas contra o `models.ts` do SPA, campo a campo.

O `serializers.py` afirmava num comentário que espelhava o `models.ts` 1:1, e
nada o verificava: acrescentar um campo de um lado e esquecer o outro não dava
erro nenhum — dava um `undefined` no ecrã do operador, semanas depois.

As listas abaixo são transcritas de
`frontend/src/app/features/payments-and-channels/channels/pos/pos-closing-credit-validation/data/models.ts`.
Ao mudar o contrato mudam-se as duas, e é isso que se pretende: que a mudança
seja deliberada dos dois lados.
"""

from typing import Any

import pytest

from app.controllers.schemas import (
    CaseReconciliationOut,
    CaseUpdateOut,
    ClosingDetailOut,
    ClosingMatchOut,
    CreditMovementOut,
    DetailCountsOut,
    DetailsPageOut,
    KeyBreakdownOut,
    PendingCaseOut,
    ReconciliationBatchOut,
    SlaSettingsOut,
    ValidationResultOut,
)

# nome do schema → (interface do models.ts, campos)
CONTRACT: dict[str, tuple[type[Any], set[str]]] = {
    "ClosingDetail": (
        ClosingDetailOut,
        {
            "id",
            "posId",
            "merchant",
            "accountNumber",
            "period",
            "key",
            "simoClosingDate",
            "operationNumber",
            "simoClosingTotal",
            "simoKeyTotal",
            "closingDescription",
            "bankaCreditDate",
            "bankaClosingTotal",
            "closingType",
            "validation",
            "difference",
            "simoClosingsCount",
            "bankaMovementsCount",
        },
    ),
    "CreditMovement": (
        CreditMovementOut,
        {"id", "key", "date", "amount", "description"},
    ),
    "PendingCase": (
        PendingCaseOut,
        {
            "id",
            "key",
            "posId",
            "period",
            "merchant",
            "accountNumber",
            "simoAmount",
            "bankaAmount",
            "type",
            "firstDate",
            "firstDateSource",
            "eTicket",
            "status",
            "statusSince",
            "resolvedAt",
            "simoClosingsCount",
            "bankaMovementsCount",
        },
    ),
    "KeyBreakdown": (
        KeyBreakdownOut,
        {"key", "closings", "movements", "case", "matches", "suggestedMatches"},
    ),
    "ClosingMatch": (
        ClosingMatchOut,
        {"closingId", "movementId"},
    ),
    "CaseReconciliation": (
        CaseReconciliationOut,
        {"case", "summary", "matches"},
    ),
    "ReconciliationBatch": (
        ReconciliationBatchOut,
        {"cases", "summary"},
    ),
    "ValidationResult": (
        ValidationResultOut,
        {
            "executionId",
            "executedAt",
            "periodStart",
            "periodEnd",
            "reportName",
            "files",
            "summary",
            "cases",
        },
    ),
    "DetailCounts": (
        DetailCountsOut,
        {"all", "match", "mismatch", "missing", "zero", "duplicated"},
    ),
    "DetailsPage": (
        DetailsPageOut,
        {"items", "total", "page", "perPage", "counts"},
    ),
    "SlaSettings": (
        SlaSettingsOut,
        {"caseSlaDays", "caseWarningDays", "updatedAt", "updatedBy"},
    ),
}


@pytest.mark.parametrize(
    ("interface", "schema", "fields"), [(name, pair[0], pair[1]) for name, pair in CONTRACT.items()]
)
def test_schema_has_exactly_models_ts_fields(
    interface: str, schema: type[Any], fields: set[str]
) -> None:
    output = set(schema.model_json_schema()["properties"])
    assert output == fields, (
        f"{interface}: o schema e o models.ts divergiram. "
        f"A mais: {sorted(output - fields)}. A menos: {sorted(fields - output)}."
    )


def test_patch_response_has_both_parts() -> None:
    """O `updateCase()` do SPA espera `{case, summary}` e nada mais."""
    assert set(CaseUpdateOut.model_json_schema()["properties"]) == {"case", "summary"}


def test_summary_indicators_are_the_dashboard_ones() -> None:
    """Os 24 campos do `ClosingSummary` (PDD §4.2.1), como o domínio os produz.

    O `summary` é o único que não é tipado no schema — é o documento JSONB tal
    como foi gravado. Confere-se aqui, na fonte, para não ficar sem verificação
    nenhuma.
    """
    from app.domain.models import ClosingSummary

    assert set(ClosingSummary().to_json_dict()) == {
        "processed",
        "matched",
        "divergent",
        "validationRate",
        "divergenceAmount",
        "openCases",
        "resolvedCases",
        "missingCount",
        "mismatchCount",
        "zeroClosings",
        "duplicatedPeriods",
        "duplicatesDiscarded",
        "bankaDuplicatesDiscarded",
        "keyCollisions",
        "unregisteredPos",
        "simoAmountMatched",
        "bankaAmountMatched",
        "simoAmountMismatched",
        "bankaAmountMismatched",
        "simoAmountMissing",
        "simoAmountDuplicated",
        "bankaAmountDuplicated",
    }
