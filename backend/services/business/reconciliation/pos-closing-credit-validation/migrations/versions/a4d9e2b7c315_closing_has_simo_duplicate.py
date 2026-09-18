"""closing has simo duplicate

Revision ID: a4d9e2b7c315
Revises: f1c3d8a92b10
Create Date: 2026-09-17 00:00:00.000000

Marca também a linha original de cada linha duplicada na SIMO, para a tabela
de fechos as ordenar juntas num bloco. Preenche as execuções já gravadas a
partir das cópias que têm.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a4d9e2b7c315"
down_revision: str | None = "f1c3d8a92b10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "closing_detail",
        sa.Column("hasSimoDuplicate", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute(
        """
        UPDATE closing_detail AS original
        SET "hasSimoDuplicate" = true
        FROM (
            SELECT DISTINCT "executionId", key, "simoClosingDate", "operationNumber",
                   "simoClosingTotal"
            FROM closing_detail
            WHERE "simoDuplicate"
        ) AS copy
        WHERE NOT original."simoDuplicate"
          AND original."executionId" = copy."executionId"
          AND original.key = copy.key
          AND original."simoClosingDate" = copy."simoClosingDate"
          AND original."operationNumber" = copy."operationNumber"
          AND original."simoClosingTotal" = copy."simoClosingTotal"
        """
    )


def downgrade() -> None:
    op.drop_column("closing_detail", "hasSimoDuplicate")
