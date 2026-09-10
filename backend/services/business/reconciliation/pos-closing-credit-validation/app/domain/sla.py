"""O prazo para o operador tratar um caso.

**Não confundir com prazo de crédito.** O `reconciliation.py` já teve uma
janela de dias úteis para decidir se um fecho tinha sido creditado a tempo, e
ela foi retirada de propósito por dar não-creditados falsos. Isto aqui é outra
coisa: conta o tempo que um caso já divergente leva **por tratar**, a partir
da data do fecho na SIMO, e não influencia validação nenhuma.

**Não há `today` neste módulo.** Quem decide que dia é hoje é o browser do
operador: o servidor corre a UTC e Moçambique não muda de hora, por isso a
data local do cliente é a data de negócio correcta. Aqui só se soma.
"""

from datetime import date, timedelta

from app.domain.errors import InvalidSlaSettingsError

DEFAULT_SLA_DAYS = 7
DEFAULT_WARNING_DAYS = 3

MAX_SLA_DAYS = 365


def deadline(closing_date: date, sla_days: int) -> date:
    """A data limite de tratamento de um fecho apurado nesse dia."""
    return closing_date + timedelta(days=sla_days)


def validate_sla(sla_days: int, warning_days: int) -> None:
    """Um prazo tem de existir, e o aviso tem de vir antes dele."""
    if not 1 <= sla_days <= MAX_SLA_DAYS:
        raise InvalidSlaSettingsError(
            f"O prazo de tratamento tem de estar entre 1 e {MAX_SLA_DAYS} dias."
        )
    if warning_days < 0:
        raise InvalidSlaSettingsError("O aviso não pode ser um número negativo de dias.")
    if warning_days >= sla_days:
        raise InvalidSlaSettingsError(
            "O aviso tem de ser menor do que o prazo — senão avisava desde o primeiro dia."
        )
