"""closing sort rank

Revision ID: b7f4c2a81d63
Revises: f3c8b1d05e92
Create Date: 2026-09-23 00:00:00.000000

A ordem por que o operador lê a tabela de fechos estava numa expressão `CASE` no
`ORDER BY`, e uma expressão não pode ser servida por índice: cada página obrigava
o Postgres a ordenar as ~18 mil linhas da execução para devolver 50.

Passa a viver numa coluna, com um índice que segue a lista de ordenação inteira.
A regra é a mesma, e a precedência do `CASE` mantém-se: os estados que pedem
trabalho ganham à marca de linha repetida, o `confere` e o `zerado` perdem-lhe.

A coluna mantém-se barata de manter porque `closing_detail` não muda depois de
gravada, com uma excepção — `set_closings_validation`, que a conciliação usa em
dezenas de linhas e que passa a reescrever também o `sortRank`.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b7f4c2a81d63"
down_revision: str | None = "f3c8b1d05e92"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_READING_ORDER = [
    "executionId",
    "sortRank",
    "posId",
    "period",
    "simoClosingDate",
    "simoDuplicate",
    "operationNumber",
]


def upgrade() -> None:
    op.add_column("closing_detail", sa.Column("sortRank", sa.SmallInteger(), nullable=True))
    op.execute(
        """
        UPDATE closing_detail
        SET "sortRank" = CASE
            WHEN validation = 'mismatch' THEN 0
            WHEN validation = 'missing' THEN 1
            WHEN validation = 'duplicated' THEN 2
            WHEN "simoDuplicate" OR "hasSimoDuplicate" THEN 3
            WHEN validation = 'match' THEN 4
            ELSE 5
        END
        """
    )
    op.alter_column("closing_detail", "sortRank", nullable=False)
    op.create_index("ix_closing_detail_reading_order", "closing_detail", _READING_ORDER)


def downgrade() -> None:
    op.drop_index("ix_closing_detail_reading_order", table_name="closing_detail")
    op.drop_column("closing_detail", "sortRank")
