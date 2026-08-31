"""Exceções de negócio de approval.

Herdam de `ErroDeNegocio` (ops_common), que já carrega o status HTTP. A camada `services/`
levanta estas; nada abaixo de `api/` conhece o FastAPI.
"""

from __future__ import annotations

from ops_common.http import Conflito, ErroDeNegocio, NaoEncontrado, TransicaoInvalida

# TODO: exceções próprias do domínio, por exemplo:
# class TicketJaFechado(TransicaoInvalida):
#     erro = "ticket_ja_fechado"

__all__ = ["Conflito", "ErroDeNegocio", "NaoEncontrado", "TransicaoInvalida"]
