"""Erros de negócio — o que pode correr mal, dito no vocabulário do domínio.

**Sem HTTP.** Estas classes não sabem o que é um 404 nem um 422: a tradução para
resposta vive em `controllers/error_handlers.py`, que é a única camada a quem
isso diz respeito. Foi por isto que saíram de `app/errors.py`, onde traziam um
`status = 422` que o adaptador de Excel importava sem ter nada que ver com o
protocolo.

A `message` é a que chega ao operador — logo, escrita em português e pronta a
mostrar, sem diagnóstico técnico pelo meio.
"""


class DomainError(Exception):
    """Raiz de tudo o que este serviço levanta de propósito."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class BusinessRuleError(DomainError):
    """Excepção de negócio do PDD: o pedido é legítimo, os dados é que não dão."""


class InvalidInputError(BusinessRuleError):
    """Ficheiro ilegível, no campo errado, ou sem as colunas que devia ter."""


class NoClosingsError(BusinessRuleError):
    """O ficheiro da SIMO não traz um único fecho válido."""


class InvalidCaseStatusError(BusinessRuleError):
    """Pediram um estado de caso que não existe."""


class UploadTooLargeError(BusinessRuleError):
    """Um dos ficheiros passa o limite de tamanho aceite."""


class NotFoundError(DomainError):
    """A execução, a chave ou o caso indicados não existem."""


class NothingToUpdateError(DomainError):
    """Vieram zero campos para alterar — o pedido não diz o que fazer.

    Não é «não encontrei» nem regra de negócio violada: é um pedido incompleto,
    e sai como tal.
    """
