# 0006 — O backend do MozaOps substitui os esqueletos da plataforma

- **Estado**: Aceite
- **Data**: 2026-08-31
- **Decisores**: Dalton Chivambo
- **Substitui**: [0002](0002-decomposicao-por-bounded-context.md),
  [0003](0003-estrutura-enxuta-em-vez-de-hexagonal.md),
  [0005](0005-ops-common-com-contexto-de-build-na-raiz.md).
  Mantém [0001](0001-monorepo-unico.md) e o princípio de
  [0004](0004-pastas-planas-departamento-como-metadado.md).

## Contexto

O repositório tinha duas metades que não se encontravam.

De um lado, `frontend/`: o SPA do **MozaOps**, as automações do
Departamento de Meios de Pagamento e Canais, com a validação de crédito de
valores de fecho já construída para POS.

Do outro, `backend/services/`: seis contextos desenhados para uma plataforma de
operações internas — `auth`, `ticketing`, `asset`, `approval`, `notification`,
`reporting` — dos quais cinco existiam como esqueleto e **nenhum tinha uma linha
de lógica de negócio**. O frontend não tinha um único ecrã para nenhum deles, e
nenhum deles servia o ecrã que o frontend tinha.

Entretanto o backend do MozaOps existe e funciona: `closing-reconciliation`, com
o parsing dos ficheiros da SIMO e do Banka, o algoritmo de reconciliação, a
persistência e a geração do relatório. E é o par exacto do frontend — o
`serializers.py` diz textualmente que espelha o `models.ts` 1:1. Verificou-se
antes de decidir: o prefixo das rotas, as seis rotas, os 21 campos do
`ClosingSummary` e o envelope de erro batem certo, campo a campo.

## Decisão

O backend passa a ser o do MozaOps. Os cinco esqueletos saem, e com eles o
`ops_common` e a infraestrutura que os servia.

Ficam as convenções do backend que veio, por serem as do código que funciona:

| | Sai | Entra |
|---|---|---|
| Pacotes | pip + setuptools, um `pyproject.toml` por serviço | **workspace `uv`**, um lock para todos |
| Layout | `src/<serviço>/` com `api/v1/controllers`, `core/`, `infrastructure/` | **`app/`** — `routes → service → repository → models`, com `domain/` puro e `infra/` |
| Isolamento de dados | schema + role por serviço numa base `ops` | **uma base e um role por serviço**, com `REVOKE CONNECT` cruzado |
| Migrações | `alembic/` | `migrations/` |
| Imagem | um Dockerfile por serviço, contexto na raiz do monorepo | **um Dockerfile**, contexto em `backend/`, serviço em `--build-arg` |
| Gateway | Oracle Service Bus | **Traefik** |
| Observabilidade | Grafana · Prometheus · Graylog (GELF) | **OpenTelemetry → Jaeger** |
| Identidade | Auth Service próprio, RS256 + JWKS | **Keycloak** (externo), ainda por ligar |
| Mensageria | RabbitMQ | *nenhuma* — não há segundo serviço para falar com |

O `domain/` deixa de ser adiado: chegou construído, e é o que a ADR 0003 dizia
para fazer no dia em que houvesse regra de negócio densa. Há — a reconciliação
tem 14 KB dela, e está isolada sem FastAPI, sem SQLAlchemy e sem openpyxl.

## Consequências

- O repositório passa a descrever o que tem: um frontend e um backend do mesmo
  produto, que falam um com o outro.
- **Copiou-se, não se portou.** Reescrever `reconciliation.py`, `parsers.py` e
  `report.py` para outro layout era mexer em lógica bancária a funcionar para
  não ganhar nada. O custo é o repositório passar a ter duas gerações de
  convenções no histórico; o benefício é não haver bugs novos em contas que já
  fechavam.
- **`libs/` fica vazio**, e é intencional — entra no dia em que houver segundo
  consumidor. É o mesmo princípio que a ADR 0005 defendia para o `ops_common`,
  aplicado com mais disciplina: lá a lib já tinha código sem ter dois clientes.
- **Uma base por serviço é isolamento mais forte** do que schema + role na
  mesma base, e o `REVOKE CONNECT` torna-o verificável: o role de um serviço não
  se liga à base do outro, e prova-se com um `psql` que falha.
- **Custo assumido**: sai plumbing escrito e testado (validação de JWT por JWKS,
  correlation-id, GELF, exportador Prometheus, cliente RabbitMQ). Nada disso
  serve a infraestrutura que fica — o Keycloak é externo, o tracing é OTel e não
  há segundo serviço — mas está no histórico (commit `4d5e2ef`) e volta se e
  quando fizer falta.
- **A autenticação fica em aberto.** O backend não valida nada e o frontend corre
  com `authDisabled: true`. É decisão consciente e datada: primeiro o fluxo
  ponta a ponta, o Keycloak a seguir. Não é estado para produção.

## Alternativas consideradas

**Portar o serviço para as nossas convenções** (`src/<serviço>/`, pip,
schema+role). Preservava as ADR 0003/0005 e o `ops_common`, mas obrigava a mover
~20 ficheiros e a reescrever imports em lógica que ninguém aqui escreveu — risco
de bug sem benefício visível para quem usa. Rejeitado.

**Manter os cinco esqueletos e juntar o `closing-reconciliation` como sexto.**
Rejeitado: o backend passaria a servir dois produtos, um deles sem frontend e
sem código. Cinco pastas a manter em dia, a aparecer em buscas e a sugerir uma
direcção que não está a ser seguida.

**Gatilho para reconsiderar**: quando existir procura real por gestão de
tickets, inventário ou aprovações genéricas dentro do MozaOps. Aí voltam como
contextos próprios — e o `git log` tem o desenho pronto.

## Nota sobre o caminho do frontend

Quando esta decisão foi tomada, o SPA vivia em `frontend/mozaops-web/`. Em
2026-09-01 subiu um nível, para `frontend/`: havia um nível de pasta a não
separar nada, porque dentro de `frontend/` só existia esse projecto. O texto
acima está com o caminho actual.

O nome `mozaops-web` não desapareceu — continua a ser o do projecto no
`angular.json`, o do pacote npm, o da imagem Docker e o do `clientId` no realm
do Keycloak. O que mudou foi só a pasta.

## Nota sobre o nome e a pasta do serviço

O serviço chamava-se `closing-reconciliation` e vivia em `backend/services/`,
sem categoria. Em 2026-09-02 passou a `closing-credit-validation`, que é como a
automação se chama de facto e o que a rota do frontend já dizia, e desceu para
`backend/services/reconciliation/` — os serviços agrupam-se por categoria de
processo, que é o que muda devagar. Ver o
[README dos serviços](../../backend/services/README.md).

A base de dados, o role e o cliente Keycloak mantêm o nome antigo: renomeá-los
obrigava a migrar a base com execuções reais e a editar o `.env` de quem já
corre isto. Os dois nomes estão registados no `service.yaml` do serviço.
