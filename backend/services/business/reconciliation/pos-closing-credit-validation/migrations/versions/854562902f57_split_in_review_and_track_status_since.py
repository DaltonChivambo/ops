"""split «em análise» into internal and simo, and track since when

Revision ID: 854562902f57
Revises: 33abfb7a4b94
Create Date: 2026-09-10 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "854562902f57"
down_revision: str | None = "33abfb7a4b94"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Um tipo novo em vez de `ADD VALUE`: o `in_review` deixa de existir, e o
    # Postgres não sabe remover um valor de um enum. Trocar o tipo inteiro
    # deixa a base sem valores mortos, e corre dentro da transacção.
    op.execute("""
        CREATE TYPE case_status_new
            AS ENUM ('pending', 'in_review_internal', 'in_review_simo', 'resolved')
    """)
    op.execute('ALTER TABLE pending_case ALTER COLUMN "status" DROP DEFAULT')
    op.execute("""
        ALTER TABLE pending_case
            ALTER COLUMN "status" TYPE case_status_new
            USING (CASE WHEN "status"::text = 'in_review'
                        THEN 'in_review_internal'
                        ELSE "status"::text
                   END)::case_status_new
    """)
    op.execute("DROP TYPE case_status")
    op.execute("ALTER TYPE case_status_new RENAME TO case_status")

    # Desde quando o caso está no estado em que está. Para os que já existem
    # não há histórico: vale a data da regularização, se houver, e senão a da
    # execução que os abriu — que é quando ficaram pendentes.
    op.add_column("pending_case", sa.Column("statusSince", sa.Date(), nullable=True))
    op.execute("""
        UPDATE pending_case pc
           SET "statusSince" = COALESCE(pc."resolvedAt", e."executedAt"::date)
          FROM execution e
         WHERE e.id = pc."executionId"
    """)
    op.execute("""
        UPDATE pending_case
           SET "statusSince" = CURRENT_DATE
         WHERE "statusSince" IS NULL
    """)
    op.alter_column("pending_case", "statusSince", nullable=False)


def downgrade() -> None:
    op.drop_column("pending_case", "statusSince")

    op.execute("CREATE TYPE case_status_old AS ENUM ('pending', 'in_review', 'resolved')")
    op.execute('ALTER TABLE pending_case ALTER COLUMN "status" DROP DEFAULT')
    op.execute("""
        ALTER TABLE pending_case
            ALTER COLUMN "status" TYPE case_status_old
            USING (CASE WHEN "status"::text LIKE 'in_review%'
                        THEN 'in_review'
                        ELSE "status"::text
                   END)::case_status_old
    """)
    op.execute("DROP TYPE case_status")
    op.execute("ALTER TYPE case_status_old RENAME TO case_status")
