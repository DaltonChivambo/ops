"""As regras do prazo de tratamento, com datas inventadas.

O prazo é a única regra do domínio que o operador pode mudar em produção, e
mudá-la mexe com o que toda a gente vê como atrasado — daí valer a pena fixar
aqui o que é e o que não é um prazo aceitável.
"""

from datetime import date

import pytest

from app.domain.errors import InvalidSlaSettingsError
from app.domain.sla import deadline, validate_sla


def test_a_data_limite_e_a_do_fecho_mais_o_prazo() -> None:
    assert deadline(date(2026, 6, 23), 7) == date(2026, 6, 30)


def test_o_prazo_atravessa_a_mudanca_de_mes() -> None:
    assert deadline(date(2026, 6, 28), 7) == date(2026, 7, 5)


def test_prazo_e_aviso_normais_passam() -> None:
    validate_sla(7, 3)


def test_aviso_a_zero_passa() -> None:
    """Zero é «não avisar antes» — legítimo, ao contrário de um negativo."""
    validate_sla(7, 0)


@pytest.mark.parametrize("dias", [0, -1, 366])
def test_prazo_fora_do_intervalo_e_recusado(dias: int) -> None:
    with pytest.raises(InvalidSlaSettingsError):
        validate_sla(dias, 0)


def test_aviso_negativo_e_recusado() -> None:
    with pytest.raises(InvalidSlaSettingsError):
        validate_sla(7, -1)


@pytest.mark.parametrize("aviso", [7, 8])
def test_aviso_a_partir_do_prazo_e_recusado(aviso: int) -> None:
    """Avisar ao fim do prazo, ou depois, era avisar desde o primeiro dia."""
    with pytest.raises(InvalidSlaSettingsError):
        validate_sla(7, aviso)
