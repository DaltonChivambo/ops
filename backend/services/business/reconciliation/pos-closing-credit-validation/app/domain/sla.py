"""O prazo para o operador tratar um caso."""

from app.domain.errors import InvalidSlaSettingsError

DEFAULT_SLA_DAYS = 7
DEFAULT_WARNING_DAYS = 3

MAX_SLA_DAYS = 365


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
