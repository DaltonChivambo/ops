"""add case sla: closing date on cases, and the settings row

Revision ID: 0fa04a56db5c
Revises: b102cbd3b593
Create Date: 2026-09-10 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0fa04a56db5c"
down_revision: str | None = "b102cbd3b593"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Anulável primeiro, para os casos que já existem poderem ser preenchidos
    # a partir dos detalhes antes de a coluna passar a obrigatória.
    op.add_column("pending_case", sa.Column("closingDate", sa.Date(), nullable=True))

    # O fecho mais antigo de cada chave — o mesmo critério do `_build_cases`.
    op.execute("""
        UPDATE pending_case pc
           SET "closingDate" = d.earliest
          FROM (SELECT "executionId", key, MIN("simoClosingDate") AS earliest
                  FROM closing_detail
                 GROUP BY "executionId", key) d
         WHERE d."executionId" = pc."executionId" AND d.key = pc.key
    """)

    # Rede de segurança: um caso sem detalhe nenhum não devia existir (são
    # escritos na mesma transacção), mas se existir não pode abortar o deploy.
    op.execute("""
        UPDATE pending_case pc
           SET "closingDate" = e."periodStart"
          FROM execution e
         WHERE e.id = pc."executionId" AND pc."closingDate" IS NULL
    """)

    op.alter_column("pending_case", "closingDate", nullable=False)

    op.create_table(
        "setting",
        sa.Column("id", sa.SmallInteger(), nullable=False),
        sa.Column("caseSlaDays", sa.Integer(), server_default="7", nullable=False),
        sa.Column("caseWarningDays", sa.Integer(), server_default="3", nullable=False),
        sa.Column("updatedAt", sa.DateTime(), nullable=False),
        sa.Column("updatedBy", sa.String(), nullable=True),
        sa.CheckConstraint("id = 1", name="ck_setting_single_row"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute("""
        INSERT INTO setting (id, "caseSlaDays", "caseWarningDays", "updatedAt", "updatedBy")
        VALUES (1, 7, 3, now() AT TIME ZONE 'UTC', NULL)
    """)


def downgrade() -> None:
    op.drop_table("setting")
    op.drop_column("pending_case", "closingDate")
