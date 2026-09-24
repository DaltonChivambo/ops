"""missing before mismatch

Revision ID: c9a3f5e1d284
Revises: b7f4c2a81d63
Create Date: 2026-09-24 00:00:00.000000

Na tabela de fechos os não creditados passam à frente dos creditados
incorrectamente. As execuções já gravadas trocam os dois valores do `sortRank`.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "c9a3f5e1d284"
down_revision: str | None = "b7f4c2a81d63"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SWAP = """
    UPDATE closing_detail
    SET "sortRank" = 1 - "sortRank"
    WHERE "sortRank" IN (0, 1)
"""


def upgrade() -> None:
    op.execute(_SWAP)


def downgrade() -> None:
    op.execute(_SWAP)
