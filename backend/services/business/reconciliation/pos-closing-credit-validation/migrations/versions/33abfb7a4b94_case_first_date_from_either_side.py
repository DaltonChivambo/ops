"""case sla counts from the first date of either side, simo or banka

Revision ID: 33abfb7a4b94
Revises: 0fa04a56db5c
Create Date: 2026-09-10 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "33abfb7a4b94"
down_revision: str | None = "0fa04a56db5c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Deixa de ser a data do fecho: passa a ser a primeira data da chave, venha
    # da SIMO ou do Banka. Chamar-lhe `closingDate` era mentira quando vem do
    # crédito, daí o nome novo.
    op.execute('ALTER TABLE pending_case RENAME COLUMN "closingDate" TO "firstDate"')

    op.execute("CREATE TYPE case_date_source AS ENUM ('simo', 'banka')")
    op.add_column(
        "pending_case",
        sa.Column(
            "firstDateSource",
            sa.Enum("simo", "banka", name="case_date_source", create_type=False),
            nullable=True,
        ),
    )

    # Recalcula os dois campos de uma vez: o mínimo de cada lado, e o lado que
    # ganhou. `LEAST` ignora nulos, e o empate fica para a SIMO — no mesmo dia,
    # o fecho vem antes do crédito que lhe corresponde.
    op.execute("""
        UPDATE pending_case pc
           SET "firstDate" = LEAST(d.simo, d.banka),
               "firstDateSource" = CASE
                   WHEN d.banka IS NOT NULL AND d.banka < d.simo THEN 'banka'
                   ELSE 'simo'
               END::case_date_source
          FROM (SELECT "executionId", key,
                       MIN("simoClosingDate") AS simo,
                       MIN("bankaCreditDate") AS banka
                  FROM closing_detail
                 GROUP BY "executionId", key) d
         WHERE d."executionId" = pc."executionId" AND d.key = pc.key
    """)

    # Um caso sem detalhe nenhum não devia existir; se existir, fica com o que
    # já lá estava e a origem por omissão, em vez de abortar o deploy.
    op.execute("""
        UPDATE pending_case
           SET "firstDateSource" = 'simo'::case_date_source
         WHERE "firstDateSource" IS NULL
    """)

    op.alter_column("pending_case", "firstDateSource", nullable=False)


def downgrade() -> None:
    op.drop_column("pending_case", "firstDateSource")
    op.execute("DROP TYPE case_date_source")
    op.execute('ALTER TABLE pending_case RENAME COLUMN "firstDate" TO "closingDate"')
