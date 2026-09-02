# closing-credit-validation

Validação de crédito de valores de fecho de POS.

Confirma que os valores de fecho dos POS apurados no Portal SIMO foram
efectivamente creditados nas contas à ordem dos comerciantes no Banka,
classifica as divergências e gera o relatório do departamento.

| | |
|---|---|
| Categoria | `reconciliation` |
| Departamento | Meios de Pagamentos e Canais (DOP) |
| Canal | POS |
| Porta | 8001 |
| Rotas | `/api/pos/validacao-credito-fecho` |

## Responsabilidade

| Papel | Quem |
|---|---|
| **Responsável pelo serviço** | Dalton Chivambo |
| **Desenvolvimento** | Dalton Chivambo |
| **Levantamento de requisitos** | Dalton Chivambo |

O responsável é quem decide sobre o serviço e a quem se pergunta primeiro. Os
outros dois campos registam quem fez o trabalho — hoje a mesma pessoa, mas são
papéis diferentes e separam-se quando a equipa crescer.

Os mesmos dados estão no [`service.yaml`](service.yaml), que é a versão legível
por máquina e alimenta o [`OWNERS.md`](../../../../OWNERS.md) da raiz. Ao mudar
um, mudar o outro.

## O que faz

Recebe três ficheiros e devolve uma execução persistida:

| Entrada | O que traz |
|---|---|
| Fechos SIMO | os valores apurados no Portal SIMO |
| Créditos Banka | o que foi efectivamente creditado |
| Lista de POS | o cadastro que liga POS a comerciante e conta |

Cruza-os pela **chave** (`posId` + período em módulo 1000), classifica cada
fecho — confere, creditado incorrectamente, não creditado, zerado, períodos
duplicados — persiste o resultado e gera o relatório em Excel.

## Organização

```
app/
├── routes.py       HTTP: entrada e saída, sem regra de negócio
├── service.py      orquestra o caso de uso
├── repository.py   acesso a dados
├── models.py       tabelas SQLAlchemy
├── serializers.py  espelha 1:1 o models.ts do frontend
├── domain/         regra pura — sem FastAPI, sem SQLAlchemy, sem openpyxl
└── infra/          parsing de Excel e geração do relatório
migrations/         Alembic
tests/
```

O `domain/` não importa nada de fora: é onde está o algoritmo de reconciliação,
e é o que permite testá-lo sem base de dados nem ficheiros.

## Correr

A partir da raiz do monorepo:

```bash
make up        # levanta a fundação e o serviço
make migrate   # Alembic sobe o schema
make test      # os testes, em contentor
```

Em desenvolvimento o serviço escuta em `localhost:8001`, que é para onde o
proxy do frontend reencaminha `/api/pos/validacao-credito-fecho`.

## Nota sobre nomes

A base de dados e o role ainda se chamam `closing_reconciliation`, o nome
anterior do serviço. Renomeá-los obrigaria a migrar a base que já tem execuções
reais e a editar o `.env` de quem já corre isto — fica para uma janela própria.
O `service.yaml` regista os dois nomes e traz o `ALTER DATABASE` pronto.
