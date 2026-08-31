"""Models ORM de approval.

`models/` é package e não ficheiro: um `models.py` único chega facilmente às centenas de linhas.
Um módulo por agregado, todos importados aqui para o Alembic os ver num só sítio.
"""

from approval.infrastructure.persistence.models.base import Base, Timestamps

# TODO: from approval.infrastructure.persistence.models.<agregado> import <Model>

__all__ = ["Base", "Timestamps"]
