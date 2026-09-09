"""O vocabulário do domínio, declarado uma vez.

Antes destes enums, os cinco estados de validação estavam escritos à mão em seis
sítios — um comentário no domínio, um tuplo nas tabelas, um `frozenset` e um
dicionário no repositório, dois mapas de rótulos na apresentação e um `if` no
serviço — sem nada que os obrigasse a concordar. Acrescentar um estado era
encontrar seis sítios de cor.

São `StrEnum`: comparam, ordenam, indexam dicionários e serializam para JSON
exactamente como as strings que substituem, por isso entram sem obrigar quem os
usa a converter nada.

**Os rótulos NÃO estão aqui**, e é de propósito. O relatório escreve «Fecho Não
Creditado_aguarda tratamento da SIMO» e o JSON escreve `missing`: são duas
apresentações do mesmo valor, e cada camada fica com a sua tabela — agora
indexada por estes membros em vez de por strings soltas.
"""

from enum import StrEnum


class Validation(StrEnum):
    """Como um fecho ficou, depois de comparado o lado SIMO com o lado Banka.

    **A ORDEM DE DECLARAÇÃO É CONTRATO DA BASE DE DADOS.** O Postgres ordena um
    enum pela ordem do `CREATE TYPE`, e o repositório pede `validation DESC` —
    ou seja, o operador lê esta lista de baixo para cima:

        duplicados · não creditados · incorrectos · conferem · zerados

    Primeiro o que exige trabalho, no fim os zerados, que não pedem nada a
    ninguém. Trocar a ordem aqui reordena a tabela que o operador vê e obriga a
    uma migração; tem de continuar igual à da migração `9e88fa0665cd`.
    """

    ZERO = "zero"
    MATCH = "match"
    MISMATCH = "mismatch"
    MISSING = "missing"
    DUPLICATED = "duplicated"


class ClosingType(StrEnum):
    """Prazo de crédito do POS, vindo do «Fecho Realtime» da Lista de POS."""

    D = "D"
    D_PLUS_1 = "D_PLUS_1"
    NA = "NA"


class CaseStatus(StrEnum):
    """Onde está o tratamento de um caso pelo operador."""

    PENDING = "pending"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"


class CaseType(StrEnum):
    """Porque é que a chave abriu caso. A ordem manda os não-creditados à frente."""

    MISSING = "missing"
    MISMATCH = "mismatch"


class UploadSlot(StrEnum):
    """Os três campos do formulário de execução.

    Os valores são camelCase porque são nomes de campos multipart — parte do
    contrato com o SPA, não identificadores de Python.
    """

    POS_LIST = "posList"
    SIMO_CLOSINGS = "simoClosings"
    BANKA_CREDITS = "bankaCredits"


# Como cada campo se chama quando a mensagem de erro tem de o nomear ao operador.
SLOT_LABELS = {
    UploadSlot.POS_LIST: "Lista de POS",
    UploadSlot.SIMO_CLOSINGS: "Fechos SIMO",
    UploadSlot.BANKA_CREDITS: "Créditos Banka",
}
