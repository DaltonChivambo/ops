"""reconciled closings count as matched

Revision ID: d7b3e91c4a26
Revises: c4e1a7d2f903
Create Date: 2026-09-16 00:00:00.000000

Os pares guardados antes de a conciliação mexer no apuramento ficaram só como
pares: o fecho continuava «períodos duplicados», e o `summary` da execução
continuava a contá-lo por tratar. Aqui acerta-se o que já existe — o fecho de
cada par passa a «confere», e o `summary` move-o de duplicados para confere,
com os montantes dos dois lados e a taxa recalculada.

A regra é a de `app/domain/matching.py::reconciled_summary`, escrita aqui outra
vez de propósito: uma migração corre contra o código do dia em que foi escrita,
e não pode mudar de comportamento se o domínio mudar depois.
"""

from collections import defaultdict
from collections.abc import Sequence
from decimal import Decimal
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "d7b3e91c4a26"
down_revision: str | None = "c4e1a7d2f903"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _validation_rate(matched: int, processed: int) -> float:
    if not processed:
        return 0.0
    rate = round(matched / processed * 100, 1)
    return min(rate, 99.9) if matched < processed else rate


def _shift(summary: dict[str, Any], closings: int, simo: Decimal, banka: Decimal) -> dict[str, Any]:
    def moved(key: str, delta: Decimal) -> float:
        return float(Decimal(str(summary.get(key, 0))) + delta)

    updated = dict(summary)
    updated["matched"] = summary.get("matched", 0) + closings
    updated["duplicatedPeriods"] = summary.get("duplicatedPeriods", 0) - closings
    updated["simoAmountMatched"] = moved("simoAmountMatched", simo)
    updated["bankaAmountMatched"] = moved("bankaAmountMatched", banka)
    updated["simoAmountDuplicated"] = moved("simoAmountDuplicated", -simo)
    updated["bankaAmountDuplicated"] = moved("bankaAmountDuplicated", -banka)
    updated["validationRate"] = _validation_rate(updated["matched"], summary.get("processed", 0))
    return updated


def _apply(from_validation: str, to_validation: str, sign: int) -> None:
    """Move os fechos com par de `from_validation` para `to_validation`, e o summary com eles."""
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            """
            SELECT d.id, d."executionId", d."simoClosingTotal", mv.amount
              FROM closing_match m
              JOIN closing_detail d ON d.id = m."closingId"
              JOIN credit_movement mv ON mv.id = m."movementId"
             WHERE d.validation = CAST(:from_validation AS validation)
            """
        ),
        {"from_validation": from_validation},
    ).all()
    if not rows:
        return

    by_execution: dict[str, list[tuple[str, Decimal, Decimal]]] = defaultdict(list)
    for closing_id, execution_id, simo, banka in rows:
        by_execution[execution_id].append((closing_id, Decimal(simo), Decimal(banka)))

    difference = "0" if to_validation == "match" else None
    for execution_id, closings in by_execution.items():
        bind.execute(
            sa.text(
                """
                UPDATE closing_detail
                   SET validation = CAST(:to_validation AS validation),
                       difference = CAST(:difference AS numeric)
                 WHERE id = ANY(:ids)
                """
            ),
            {
                "to_validation": to_validation,
                "difference": difference,
                "ids": [closing_id for closing_id, _, _ in closings],
            },
        )
        summary = bind.execute(
            sa.text("SELECT summary FROM execution WHERE id = :id"), {"id": execution_id}
        ).scalar_one()
        shifted = _shift(
            summary,
            sign * len(closings),
            sign * sum((simo for _, simo, _ in closings), Decimal(0)),
            sign * sum((banka for _, _, banka in closings), Decimal(0)),
        )
        bind.execute(
            sa.text("UPDATE execution SET summary = :summary WHERE id = :id").bindparams(
                sa.bindparam("summary", type_=JSONB)
            ),
            {"summary": shifted, "id": execution_id},
        )


def upgrade() -> None:
    _apply("duplicated", "match", 1)


def downgrade() -> None:
    _apply("match", "duplicated", -1)
