# pos-closing-credit-validation

Validação de crédito de valores de fecho de POS.

Confirma que os valores de fecho dos POS apurados no Portal SIMO foram
efectivamente creditados nas contas à ordem dos comerciantes no Banka,
classifica as divergências e gera o relatório do departamento.

Específico do POS — ATM e Quiosques, quando chegar a vez, ganham os seus
próprios serviços em vez de partilhar este.

| | |
|---|---|
| Categoria | `business/reconciliation` |
| Departamento | Meios de Pagamentos e Canais (DOP) |
| Canal | POS |
| Porta | 8000 no contentor · 8101 publicada em desenvolvimento |
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
por máquina e alimenta o [`OWNERS.md`](../../../../../OWNERS.md) da raiz. Ao mudar
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

Cinco camadas, num só sentido — ver o
[`ARCHITECTURE.md`](../../../../../ARCHITECTURE.md).

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
make check SERVICES=backend/services/business/reconciliation/pos-closing-credit-validation
```

O `check` confirma que o lock e os requirements estão em dia e corre ruff, mypy e pytest no
estágio `test` da imagem. Só com Docker, dentro desta pasta, é o mesmo que:

```bash
docker build --target test -t pos-closing-credit-validation:test .
docker run --rm pos-closing-credit-validation:test
```

## Na rede do banco: onde se mexe

Nada neste serviço tem um endereço escrito. Tudo se mete em `ops/.env` (a partir do
`ops/.env.example`), ou nas variáveis da pipeline.

**Para construir a imagem** (o `Dockerfile` desta pasta):

| Variável | O que é |
|---|---|
| `IMAGE_REGISTRY`, `IMAGE_NAMESPACE` | Harbor: de onde vem a imagem `python:3.14-slim-trixie` |
| `PYPI_INDEX_URL`, `PYPI_TRUSTED_HOST` | Nexus: de onde vêm os pacotes do `requirements.txt` |

**Para correr** (o `app/settings.py`):

| Variável | O que é |
|---|---|
| `DATABASE_URL` | a base do serviço. O `docker-compose.yml` monta-a a partir de `DB_RECONCILIATION_USER` e `DB_RECONCILIATION_PASSWORD`; fora do compose, passa-se inteira |
| `AUTH_ISSUER`, `AUTH_JWKS_URL` | quem emite os tokens do GEEA e onde estão as chaves; os mesmos valores do `auth-service` |
| `AUTH_ALLOWED_AZP`, `AUTH_CLIENT_ID` | que cliente conta; `qa-mozaops` no QAS |
| `AUTH_AREAS`, `AUTH_AREA_USERS` | que unidades e pessoas abrem cada área |
| `AUTH_SERVICE_AREA`, `AUTH_SERVICE_ID` | a área desta automação e o id dela |
| `MAX_UPLOAD_MB` | tamanho máximo de cada ficheiro carregado |

Este serviço não faz login: só valida os tokens. Mas vai buscar as chaves ao `AUTH_JWKS_URL`,
por isso o contentor tem de chegar ao host do GEEA.

Construir só este serviço, a partir do Harbor e do Nexus, dentro desta pasta:

```bash
docker build \
  --build-arg IMAGE_REGISTRY=<host do Harbor> \
  --build-arg IMAGE_NAMESPACE=<projecto do Harbor> \
  --build-arg PYPI_INDEX_URL=<URL do Nexus, terminado em /simple/> \
  --build-arg PYPI_TRUSTED_HOST=<host do Nexus> \
  -t pos-closing-credit-validation:local .
```

Ou, a partir da raiz, `ci/service.sh build backend/services/business/reconciliation/pos-closing-credit-validation`,
que lê os mesmos valores do `ops/.env`.

## Testes

| Ficheiro | O que cobre | Precisa de quê |
|---|---|---|
| `test_api.py` | as seis rotas, os estados de erro e o envelope | nada |
| `test_contract.py` | os schemas contra o `models.ts` do SPA | nada |
| `test_reconciliation_rules.py` | as regras da reconciliação, com dados inventados | nada |
| `test_report.py` | o relatório Excel: o que cai em cada folha, e se as três fecham entre si | nada |
| `test_reconciliation.py` | os números reais: 18 138 fechos, 99,3% | os três `.xlsx` |

O último **salta-se sozinho** sem os ficheiros do departamento — são dados
bancários e não são versionados. Para o correr, pô-los em `tests/fixtures/` como
`pos-list.xlsx`, `simo-closings.xlsx` e `banka-credits.xlsx`.

Em desenvolvimento o serviço escuta em `localhost:8101`, que é para onde o
proxy do frontend reencaminha `/api/pos/validacao-credito-fecho`.
