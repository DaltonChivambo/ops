"""add closing_match: fecho a fecho nas chaves de períodos duplicados

Revision ID: c4e1a7d2f903
Revises: 854562902f57
Create Date: 2026-09-16 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c4e1a7d2f903"
down_revision: str | None = "854562902f57"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "closing_match",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("executionId", sa.String(length=36), nullable=False),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("closingId", sa.String(length=36), nullable=False),
        sa.Column("movementId", sa.String(length=36), nullable=False),
        sa.Column("matchedAt", sa.DateTime(), nullable=False),
        sa.Column("matchedBy", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["executionId"], ["execution.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["closingId"], ["closing_detail.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["movementId"], ["credit_movement.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        # Um par por fecho e um por movimento: a regra do domínio, também na base.
        sa.UniqueConstraint("closingId"),
        sa.UniqueConstraint("movementId"),
    )
    op.create_index(
        "ix_closing_match_execution_key", "closing_match", ["executionId", "key"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_closing_match_execution_key", table_name="closing_match")
    op.drop_table("closing_match")
