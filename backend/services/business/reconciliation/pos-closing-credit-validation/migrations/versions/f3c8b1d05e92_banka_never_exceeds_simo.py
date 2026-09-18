"""banka never exceeds simo

Revision ID: f3c8b1d05e92
Revises: e5a72c9f1b48
Create Date: 2026-09-18 00:00:00.000000

O lado do Banka das chaves de períodos repetidos passou a ter tecto no lado da
SIMO: a conciliação parte dos fechos, e um crédito só conta na medida em que há
fecho que ele possa pagar. Nestas chaves havia a mais, porque um período real
diferente do mesmo POS colide em `% 1000` e traz dinheiro de outra chave — e
isso punha o Banka acima da SIMO no total do apuramento.

Aqui só se aplica o tecto ao que está gravado, em vez de recalcular: assim
respeita-se o que as conciliações já ajustaram no `summary`.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "f3c8b1d05e92"
down_revision: str | None = "e5a72c9f1b48"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE execution
        SET summary = summary || jsonb_build_object(
            'bankaAmountDuplicated',
            LEAST(
                (summary->>'bankaAmountDuplicated')::numeric,
                (summary->>'simoAmountDuplicated')::numeric
            )
        )
        WHERE summary ? 'bankaAmountDuplicated'
          AND summary ? 'simoAmountDuplicated'
          AND (summary->>'bankaAmountDuplicated')::numeric
              > (summary->>'simoAmountDuplicated')::numeric
        """
    )


def downgrade() -> None:
    """Não se desfaz: o excesso que foi cortado não ficou guardado em lado nenhum.

    Correr a validação outra vez sobre os mesmos ficheiros devolve o apuramento
    completo, com a regra que estiver em vigor.
    """
