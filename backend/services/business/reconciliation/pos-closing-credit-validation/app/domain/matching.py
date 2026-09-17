"""Conciliação fecho a fecho numa chave de períodos duplicados.

Uma chave «períodos duplicados» não se valida por soma (ver
`domain/reconciliation.py`): tem vários fechos na SIMO, ou vários movimentos no
Banka, e a soma de um lado contra a soma do outro não diz qual crédito pagou qual
fecho. Quem desfaz isso é o operador, emparelhando um fecho com um movimento.

**A regra do par é a mesma da reconciliação: valor exactamente igual.** Sem
tolerância, pela mesma razão — um crédito que difere num cêntimo não é o crédito
daquele fecho, é outro problema. E cada lado entra num par só: um movimento não
paga dois fechos, e um fecho não é pago duas vezes.

Uma chave está conciliada quando **todos os fechos da SIMO** têm par. O que
se valida são os fechos da SIMO contra o Banka: os movimentos do Banka que sobram
(de outro período real que cai na mesma chave, `período % 1000`) não são fechos,
e não seguram nada.

Camada de domínio: sem I/O, sem tabelas — recebe os dois lados já lidos.
"""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from .errors import InvalidMatchError
from .reconciliation import validation_rate


@dataclass(frozen=True, slots=True)
class MatchSide:
    """Um fecho da SIMO ou um movimento do Banka, no que interessa para emparelhar."""

    id: str
    date: date | None
    amount: Decimal


@dataclass(frozen=True, slots=True)
class Match:
    closing_id: str
    movement_id: str


def _by_date(side: MatchSide) -> tuple[bool, date, str]:
    # Sem data vai para o fim; o id desempata, para a sugestão sair sempre igual.
    return (side.date is None, side.date or date.min, side.id)


def suggest_matches(closings: Sequence[MatchSide], movements: Sequence[MatchSide]) -> list[Match]:
    """Os pares que se podem fazer sem ambiguidade de valor — a sugestão do ecrã.

    Dentro de cada valor, emparelha por ordem de data: o fecho mais antigo com o
    crédito mais antigo. Quando há mais fechos do que créditos desse valor (ou o
    contrário), os que sobram ficam sem par — e é isso que o ecrã mostra como
    «não é possível conciliar todos».
    """
    movements_by_amount: dict[Decimal, list[MatchSide]] = defaultdict(list)
    for movement in sorted(movements, key=_by_date):
        movements_by_amount[movement.amount].append(movement)

    matches: list[Match] = []
    for closing in sorted(closings, key=_by_date):
        available = movements_by_amount.get(closing.amount)
        if available:
            matches.append(Match(closing.id, available.pop(0).id))
    return matches


def validate_matches(
    matches: Sequence[Match],
    closings: Sequence[MatchSide],
    movements: Sequence[MatchSide],
) -> None:
    """Recusa um conjunto de pares que o operador não podia ter feito.

    As mensagens chegam ao operador: dizem o que está errado no par, não no
    pedido.
    """
    closing_by_id = {closing.id: closing for closing in closings}
    movement_by_id = {movement.id: movement for movement in movements}
    used_closings: set[str] = set()
    used_movements: set[str] = set()

    for match in matches:
        closing = closing_by_id.get(match.closing_id)
        movement = movement_by_id.get(match.movement_id)
        if closing is None or movement is None:
            raise InvalidMatchError(
                "Um dos pares indica um fecho ou um crédito que não pertence a esta chave. "
                "Volte a abrir o caso e concilie de novo."
            )
        if match.closing_id in used_closings:
            raise InvalidMatchError("O mesmo fecho não pode ser conciliado com dois créditos.")
        if match.movement_id in used_movements:
            raise InvalidMatchError("O mesmo crédito do Banka não pode pagar dois fechos.")
        if closing.amount != movement.amount:
            raise InvalidMatchError(
                "Só se concilia um fecho com um crédito de valor exactamente igual."
            )
        used_closings.add(match.closing_id)
        used_movements.add(match.movement_id)


def is_fully_matched(matches: Sequence[Match], closings: Sequence[MatchSide]) -> bool:
    """Todos os fechos da SIMO têm par — os créditos podem sobrar (ver o topo)."""
    matched = {match.closing_id for match in matches}
    return bool(closings) and all(closing.id in matched for closing in closings)


# ─── O que a conciliação muda no apuramento ─────────────────────────────────


@dataclass(frozen=True, slots=True)
class MatchEffect:
    """O peso de um conjunto de pares no apuramento: fechos e montantes de cada lado."""

    closings: int
    simo_amount: Decimal
    banka_amount: Decimal


def match_effect(
    matches: Sequence[Match],
    closings: Sequence[MatchSide],
    movements: Sequence[MatchSide],
) -> MatchEffect:
    closing_by_id = {closing.id: closing for closing in closings}
    movement_by_id = {movement.id: movement for movement in movements}
    paired = [
        (closing_by_id[match.closing_id], movement_by_id[match.movement_id])
        for match in matches
        if match.closing_id in closing_by_id and match.movement_id in movement_by_id
    ]
    return MatchEffect(
        closings=len(paired),
        simo_amount=sum((closing.amount for closing, _ in paired), Decimal(0)),
        banka_amount=sum((movement.amount for _, movement in paired), Decimal(0)),
    )


def reconciled_summary(
    summary: dict[str, Any], before: MatchEffect, after: MatchEffect
) -> dict[str, Any]:
    """O `summary` gravado, com a conciliação de uma chave reflectida nele.

    **Um fecho conciliado confere.** Ligado a um crédito de valor exactamente
    igual, é o que a reconciliação teria dito se a chave não fosse ambígua — por
    isso sai de «períodos duplicados» e entra em «crédito confere», com os
    montantes dos dois lados, e a taxa de validação recalcula-se. Desfazer um par
    faz o caminho inverso.

    Aplica-se a diferença entre os pares de antes e os de agora, e não os pares
    de agora por cima: guardar o mesmo conjunto duas vezes não pode contar duas.
    O documento é JSON (camelCase, montantes em `float`), e sai na mesma forma.
    """
    closings = after.closings - before.closings
    simo = after.simo_amount - before.simo_amount
    banka = after.banka_amount - before.banka_amount

    def shifted(key: str, delta: Decimal) -> float:
        return float(Decimal(str(summary.get(key, 0))) + delta)

    updated = dict(summary)
    updated["matched"] = summary.get("matched", 0) + closings
    updated["duplicatedPeriods"] = summary.get("duplicatedPeriods", 0) - closings
    updated["simoAmountMatched"] = shifted("simoAmountMatched", simo)
    updated["bankaAmountMatched"] = shifted("bankaAmountMatched", banka)
    updated["simoAmountDuplicated"] = shifted("simoAmountDuplicated", -simo)
    updated["bankaAmountDuplicated"] = shifted("bankaAmountDuplicated", -banka)
    updated["validationRate"] = validation_rate(updated["matched"], summary.get("processed", 0))
    return updated
