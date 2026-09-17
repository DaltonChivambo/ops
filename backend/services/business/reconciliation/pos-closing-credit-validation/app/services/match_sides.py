"""As linhas guardadas, na forma que `domain/matching.py` sabe emparelhar.

Vive nos serviços e não no domínio porque conhece as tabelas; e fica num
sítio só porque o detalhe da chave (sugere) e o caso (valida) têm de ver os
dois lados exactamente da mesma maneira.
"""

from app.domain.matching import MatchSide
from app.infrastructure.tables import ClosingDetail, CreditMovement


def closing_side(row: ClosingDetail) -> MatchSide:
    return MatchSide(id=row.id, date=row.simo_closing_date, amount=row.simo_closing_total)


def movement_side(row: CreditMovement) -> MatchSide:
    return MatchSide(id=row.id, date=row.movement_date, amount=row.amount)
