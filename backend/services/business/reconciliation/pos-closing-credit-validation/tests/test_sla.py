"""As regras do prazo de tratamento, com datas inventadas.

O prazo é a única regra do domínio que o operador pode mudar em produção, e
mudá-la mexe com o que toda a gente vê como atrasado — daí valer a pena fixar
aqui o que é e o que não é um prazo aceitável.
"""

import pytest

from app.domain.errors import InvalidSlaSettingsError
from app.domain.sla import validate_sla


def test_normal_sla_and_warning_pass() -> None:
    validate_sla(7, 3)


def test_zero_warning_passes() -> None:
    """Zero é «não avisar antes» — legítimo, ao contrário de um negativo."""
    validate_sla(7, 0)


@pytest.mark.parametrize("days", [0, -1, 366])
def test_sla_out_of_range_is_rejected(days: int) -> None:
    with pytest.raises(InvalidSlaSettingsError):
        validate_sla(days, 0)


def test_negative_warning_is_rejected() -> None:
    with pytest.raises(InvalidSlaSettingsError):
        validate_sla(7, -1)


@pytest.mark.parametrize("warning", [7, 8])
def test_warning_at_or_after_sla_is_rejected(warning: int) -> None:
    """Avisar ao fim do prazo, ou depois, era avisar desde o primeiro dia."""
    with pytest.raises(InvalidSlaSettingsError):
        validate_sla(7, warning)
