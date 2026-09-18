"""execution counts simo duplicates

Revision ID: e5a72c9f1b48
Revises: a4d9e2b7c315
Create Date: 2026-09-18 00:00:00.000000

O operador passa a poder mandar contar o dinheiro das linhas repetidas do export
da SIMO na reconciliação de montantes. A decisão é da execução inteira e fica
aqui, porque o relatório sai com ela — não é preferência de quem olha.

Não mexe em estados nem em casos: uma linha repetida no ficheiro não é um fecho
novo. As execuções já gravadas ficam a `false`, que é como foram apuradas, e
recebem o montante dessas linhas, que até agora ninguém somava.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e5a72c9f1b48"
down_revision: str | None = "a4d9e2b7c315"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "execution",
        sa.Column("countSimoDuplicates", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    # O `summary` é JSONB e o SPA lê-o tal como está: sem estas chaves, o botão
    # aparecia desligado nas execuções antigas por ausência e não por decisão, e
    # o montante das linhas repetidas ficava por somar.
    op.execute(
        """
        UPDATE execution AS e
        SET summary = e.summary || jsonb_build_object(
            'countSimoDuplicates', false,
            'simoAmountDuplicateRows', COALESCE(repeated.simo, 0),
            'bankaAmountDuplicateRows', COALESCE(repeated.banka, 0)
        )
        FROM (
            -- Por chave: o que as linhas repetidas somam, e o crédito que lhes
            -- corresponde — o delas próprias, limitado ao que a chave tem mesmo
            -- creditado. Ver `_duplicate_rows_credit` no domínio.
            SELECT ex.id,
                   SUM(k.repeated) AS simo,
                   SUM(LEAST(k.repeated, k.credited)) AS banka
            FROM execution AS ex
            LEFT JOIN (
                SELECT d."executionId",
                       SUM(d."simoClosingTotal") FILTER (WHERE d."simoDuplicate") AS repeated,
                       MAX(COALESCE(d."bankaClosingTotal", 0)) AS credited
                FROM closing_detail AS d
                GROUP BY d."executionId", d.key
                HAVING SUM(d."simoClosingTotal") FILTER (WHERE d."simoDuplicate") IS NOT NULL
            ) AS k ON k."executionId" = ex.id
            GROUP BY ex.id
        ) AS repeated
        WHERE repeated.id = e.id
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE execution
        SET summary = summary - 'countSimoDuplicates' - 'simoAmountDuplicateRows'
                      - 'bankaAmountDuplicateRows'
        """
    )
    op.drop_column("execution", "countSimoDuplicates")
