"""Erros de negócio — o que pode correr mal, dito no vocabulário do domínio."""


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


class InvalidETicketError(BusinessRuleError):
    """O e-Ticket não tem forma de referência (ver `domain/e_ticket.py`)."""


class InvalidMatchError(BusinessRuleError):
    """Um par fecho ↔ crédito que não se pode fazer (ver `domain/matching.py`)."""


class InvalidSlaSettingsError(BusinessRuleError):
    """O prazo de tratamento pedido não faz sentido (ver `domain/sla.py`)."""


class UploadTooLargeError(BusinessRuleError):
    """Um dos ficheiros passa o limite de tamanho aceite."""


class NotFoundError(DomainError):
    """A execução, a chave ou o caso indicados não existem."""


class NothingToUpdateError(DomainError):
    """Vieram zero campos para alterar — o pedido não diz o que fazer."""
