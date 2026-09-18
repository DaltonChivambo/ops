"""closing simo duplicate flag

Revision ID: f1c3d8a92b10
Revises: d7b3e91c4a26
Create Date: 2026-09-17 00:00:00.000000

As linhas que o export da SIMO traz duplicadas passam a ser gravadas: contam
como fechos, com a validação da original, e ficam marcadas por esta coluna.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f1c3d8a92b10"
down_revision: str | None = "d7b3e91c4a26"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "closing_detail",
        sa.Column("simoDuplicate", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("closing_detail", "simoDuplicate")
