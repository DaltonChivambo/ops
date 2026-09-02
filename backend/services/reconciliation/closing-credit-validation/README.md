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
| Porta | 8000 no contentor · 8001 publicada em desenvolvimento |
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

Cinco camadas, num só sentido — ver a
[ADR 0008](../../../../docs/adr/0008-cinco-camadas-por-servico.md).

```
app/
├── main.py            junta as peças: a app, o router, os handlers, o /health
├── settings.py        o que o serviço lê do ambiente — e só o que lê
├── pagination.py      page/perPage → skip/take
├── controllers/       HTTP: rotas, schemas Pydantic, dependências, erros → estados
├── services/          os casos de uso
├── domain/            a regra pura, e o vocabulário
├── repositories/      o único acesso a dados
└── infrastructure/    sessão, tabelas e a leitura/escrita de Excel
migrations/            Alembic
tests/
```

O `domain/` não importa nada de fora — sem FastAPI, sem SQLAlchemy, sem
openpyxl. É onde está o algoritmo de reconciliação e o `vocabulary.py` que
declara, uma vez, os estados de validação, os tipos de fecho, os estados de caso
e os campos de upload. É também o que permite testar a regra sem base de dados
nem ficheiros.

Os erros do domínio não sabem o que é um 404: a tabela que os traduz vive em
`controllers/error_handlers.py`.

## Correr

A partir da raiz do monorepo:

```bash
make up        # levanta a fundação e o serviço
make migrate   # Alembic sobe o schema
make lint      # ruff (regras e formato) e mypy --strict
make test      # os testes, em contentor
```

## Testes

| Ficheiro | O que cobre | Precisa de quê |
|---|---|---|
| `test_api.py` | as seis rotas, os estados de erro e o envelope | nada |
| `test_contract.py` | os schemas contra o `models.ts` do SPA | nada |
| `test_reconciliation_rules.py` | as regras da reconciliação, com dados inventados | nada |
| `test_reconciliation.py` | os números reais: 18 138 fechos, 99,3% | os três `.xlsx` |

O último **salta-se sozinho** sem os ficheiros do departamento — são dados
bancários e não são versionados. Para o correr, pô-los em `tests/fixtures/` como
`pos-list.xlsx`, `simo-closings.xlsx` e `banka-credits.xlsx`.

Em desenvolvimento o serviço escuta em `localhost:8001`, que é para onde o
proxy do frontend reencaminha `/api/pos/validacao-credito-fecho`.

## Nota sobre nomes

A base de dados e o role ainda se chamam `closing_reconciliation`, o nome
anterior do serviço. Renomeá-los obrigaria a migrar a base que já tem execuções
reais e a editar o `.env` de quem já corre isto — fica para uma janela própria.
O `service.yaml` regista os dois nomes e traz o `ALTER DATABASE` pronto.
