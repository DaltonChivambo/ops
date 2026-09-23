"""O vocabulário do domínio, declarado uma vez."""

from enum import StrEnum


class Validation(StrEnum):
    """Como um fecho ficou, depois de comparado o lado SIMO com o lado Banka.

    A ordem de declaração é contrato da base de dados: o Postgres ordena o enum
    por ela, e mudá-la obriga a migração. Igual à da `9e88fa0665cd`.
    """

    ZERO = "zero"
    MATCH = "match"
    MISMATCH = "mismatch"
    MISSING = "missing"
    DUPLICATED = "duplicated"


class RepeatedClosings(StrEnum):
    """O que a lista de fechos faz aos fechos repetidos na SIMO."""

    ALL = "all"
    ONLY = "only"
    WITHOUT = "without"


class ClosingType(StrEnum):
    """Prazo de crédito do POS, vindo do «Fecho Realtime» da Lista de POS."""

    D = "D"
    D_PLUS_1 = "D_PLUS_1"
    NA = "NA"


class CaseStatus(StrEnum):
    """Onde está o tratamento de um caso."""

    PENDING = "pending"
    IN_REVIEW_INTERNAL = "in_review_internal"
    IN_REVIEW_SIMO = "in_review_simo"
    RESOLVED = "resolved"


class CaseType(StrEnum):
    """Porque é que a chave abriu caso; a ordem de declaração manda a leitura."""

    MISSING = "missing"
    MISMATCH = "mismatch"
    DUPLICATED = "duplicated"


class CaseDateSource(StrEnum):
    """De que lado veio a primeira data da chave — a que abre o prazo."""

    SIMO = "simo"
    BANKA = "banka"


class UploadSlot(StrEnum):
    """Os três campos do formulário de execução."""

    POS_LIST = "posList"
    SIMO_CLOSINGS = "simoClosings"
    BANKA_CREDITS = "bankaCredits"


# Como cada campo se chama quando a mensagem de erro tem de o nomear ao operador.
SLOT_LABELS = {
    UploadSlot.POS_LIST: "Lista de POS",
    UploadSlot.SIMO_CLOSINGS: "Fechos SIMO",
    UploadSlot.BANKA_CREDITS: "Créditos Banka",
}
