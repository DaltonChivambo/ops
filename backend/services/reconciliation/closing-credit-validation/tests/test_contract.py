"""Os schemas contra o `models.ts` do SPA, campo a campo.

O `serializers.py` afirmava num comentário que espelhava o `models.ts` 1:1, e
nada o verificava: acrescentar um campo de um lado e esquecer o outro não dava
erro nenhum — dava um `undefined` no ecrã do operador, semanas depois.

As listas abaixo são transcritas de
`frontend/src/app/features/payments-and-channels/channels/closing-reconciliation/data/models.ts`.
Ao mudar o contrato mudam-se as duas, e é isso que se pretende: que a mudança
seja deliberada dos dois lados.
"""

from typing import Any

import pytest

from app.controllers.schemas import (
    CaseUpdateOut,
    ClosingDetailOut,
    CreditMovementOut,
    DetailCountsOut,
    DetailsPageOut,
    KeyBreakdownOut,
    PendingCaseOut,
    ValidationResultOut,
)

# nome do schema → (interface do models.ts, campos)
CONTRATO: dict[str, tuple[type[Any], set[str]]] = {
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
            "eTicket",
            "status",
            "resolvedAt",
        },
    ),
    "KeyBreakdown": (
        KeyBreakdownOut,
        {"key", "closings", "movements", "case"},
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
}


@pytest.mark.parametrize(
    ("interface", "schema", "campos"), [(nome, par[0], par[1]) for nome, par in CONTRATO.items()]
)
def test_schema_tem_exactamente_os_campos_do_models_ts(
    interface: str, schema: type[Any], campos: set[str]
) -> None:
    saida = set(schema.model_json_schema()["properties"])
    assert saida == campos, (
        f"{interface}: o schema e o models.ts divergiram. "
        f"A mais: {sorted(saida - campos)}. A menos: {sorted(campos - saida)}."
    )


def test_resposta_do_patch_tem_os_dois_lados() -> None:
    """O `updateCase()` do SPA espera `{case, summary}` e nada mais."""
    assert set(CaseUpdateOut.model_json_schema()["properties"]) == {"case", "summary"}


def test_os_indicadores_do_summary_sao_os_do_dashboard() -> None:
    """Os 21 campos do `ClosingSummary` (PDD §4.2.1), como o domínio os produz.

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
