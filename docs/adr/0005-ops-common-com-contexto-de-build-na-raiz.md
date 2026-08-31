# 0005 — `ops_common` com contexto de build na raiz

- **Estado**: Substituído por [0006](0006-backend-mozaops-substitui-esqueletos.md)
- **Data**: 2026-08-25
- **Decisores**: Dalton Chivambo

## Contexto

Os seis serviços partilham código transversal: verificação de JWT contra o JWKS do Auth, logging
GELF para o Graylog com correlation-id, exportador Prometheus, cliente RabbitMQ e envelope de
evento, error handlers e paginação HTTP.

Num monorepo ([0001](0001-monorepo-unico.md)), o `docker build` de um serviço tem de conseguir
ver esse código — e por omissão o contexto de build é a pasta do serviço, que não o inclui.

## Decisão

`backend/libs/ops_common/` vive no monorepo e é consumido com **contexto de build na raiz**, sem
índice pip privado:

```yaml
# infra/compose/docker-compose.yml
services:
  asset:
    build:
      context: ../..                          # raiz do monorepo
      dockerfile: backend/services/asset/Dockerfile
```

A regra que delimita o conteúdo da lib: **`ops_common` só leva plumbing.** Nunca entidades de
negócio, nunca models SQLAlchemy partilhados.

## Consequências

- Uma correção na validação do JWT toca a lib e os seis serviços **num só commit, num só PR**,
  com um só build a validar tudo. É a única vantagem real do monorepo, e esta decisão é o que a
  torna acessível.
- Não é preciso repositório de artefactos (Nexus, Artifactory) nem pipeline própria da lib.
- **Custo, a assumir explicitamente**: `docker build` a partir da pasta do serviço **deixa de
  funcionar**. Todos os builds passam pelo `docker compose` ou pelo Jenkins. Vale a pena
  documentar isto no README de cada serviço, porque é a primeira coisa que surpreende quem chega.
- **Custo**: o contexto de build é maior, o que torna um `.dockerignore` cuidado obrigatório e não
  opcional.
- **Risco a vigiar**: no dia em que dois serviços importarem a mesma tabela `Cliente` da lib,
  deixam de poder fazer deploy em separado e o resultado é um monólito distribuído — exactamente
  o problema que [0002](0002-decomposicao-por-bounded-context.md) existe para evitar. A regra
  "só plumbing" é o que protege contra isso, e deve ser aplicada em revisão de código.

## Alternativas consideradas

**Índice pip privado com a lib versionada.** Contexto de build simples e adoção faseada por
serviço. Rejeitado por agora: exige repositório de artefactos e pipeline própria, e substitui a
mudança atómica por publicar uma versão, esperar, e abrir seis PRs para a adotar — a burocracia
do multi-repo dentro de um monorepo.

*Gatilho para reconsiderar*: ser preciso que um serviço adote uma versão nova da lib meses antes
ou depois dos outros.

**Imagem base `ops-python-base`** com as dependências comuns e a lib já instaladas. Resolve um
problema diferente — tempo de build — que ainda não se sabe se existe. Acrescentá-la depois não
obriga a mexer no código da lib.

*Gatilho para reconsiderar*: os tempos de build no Jenkins incomodarem.
