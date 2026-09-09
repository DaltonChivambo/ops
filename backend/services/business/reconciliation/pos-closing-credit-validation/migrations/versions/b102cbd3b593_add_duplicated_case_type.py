"""add duplicated case type

Revision ID: b102cbd3b593
Revises: 9e88fa0665cd
Create Date: 2026-09-09 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "b102cbd3b593"
down_revision: str | None = "9e88fa0665cd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Chaves com período duplicado passam a abrir caso, tal como não-creditado
    # e incorrecto — precisa de um terceiro valor no enum nativo do Postgres.
    op.execute("ALTER TYPE case_type ADD VALUE IF NOT EXISTS 'duplicated'")


def downgrade() -> None:
    # Postgres não suporta remover um valor de um enum — irreversível de propósito.
    raise NotImplementedError("Não é possível remover um valor de enum no Postgres.")
