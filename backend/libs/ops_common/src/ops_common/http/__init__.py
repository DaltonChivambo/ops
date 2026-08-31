from ops_common.http.client import ServiceClient, ServicoIndisponivel
from ops_common.http.errors import (
    Conflito,
    ErroDeNegocio,
    ErroResposta,
    NaoEncontrado,
    TransicaoInvalida,
    register_error_handlers,
)
from ops_common.http.pagination import Pagina, ParametrosPagina, parametros_pagina

__all__ = [
    "Conflito",
    "ErroDeNegocio",
    "ErroResposta",
    "NaoEncontrado",
    "Pagina",
    "ParametrosPagina",
    "ServiceClient",
    "ServicoIndisponivel",
    "TransicaoInvalida",
    "parametros_pagina",
    "register_error_handlers",
]
