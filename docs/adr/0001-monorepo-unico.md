# 0001 — Monorepo único no Bitbucket

- **Estado**: Aceite
- **Data**: 2026-08-25
- **Decisores**: Dalton Chivambo

## Contexto

A plataforma OPS arranca do zero, com seis microserviços previstos, um frontend Angular, a
configuração de infraestrutura (Docker Compose, Postgres, RabbitMQ, observabilidade) e as
pipelines Jenkins. É preciso decidir como versionar tudo isto no Bitbucket antes de escrever
a primeira linha.

A equipa é pequena e não há, à partida, equipas de desenvolvimento separadas por departamento.

## Decisão

Um único repositório `ops/`, contendo `backend/services/*`, `backend/libs/*`, `frontend/`,
`infra/`, `qa/`, `ci/` e `docs/`.

O Jenkins deteta que serviços foram alterados pelo caminho dos ficheiros no commit e constrói
apenas esses.

## Consequências

- Uma mudança transversal — corrigir a validação do JWT, mudar o formato dos logs — toca a lib
  partilhada e os seis serviços **num só commit, num só PR, com um só build a validar tudo**.
- Não é preciso repositório de artefactos nem publicar versões da lib partilhada
  (ver [0005](0005-ops-common-com-contexto-de-build-na-raiz.md)).
- A consistência entre serviços é fácil de manter e de verificar.
- **Custo**: o build tem de ser seletivo por caminho, senão qualquer commit reconstrói tudo.
  Isto é trabalho real no `ci/Jenkinsfile` e não pode ser adiado indefinidamente.
- **Custo**: permissões por pasta no Bitbucket são mais difíceis de impor do que com repos
  separados. Não é um problema hoje; passaria a ser se cada departamento tivesse equipa própria.

## Alternativas consideradas

**Um repositório por microserviço.** Dá autonomia total por equipa e pipelines triviais. Foi
rejeitado porque a lib partilhada passaria a exigir um índice pip privado, e cada mudança
transversal obrigaria a publicar uma versão nova e abrir seis PRs para a adotar — pagar a
burocracia do multi-repo sem ter as equipas independentes que a justificam.

**Híbrido** (plataforma e libs num repo, serviços em repos próprios). Rejeitado por juntar as
desvantagens dos dois: continua a precisar de publicação da lib, e acrescenta a pergunta de em
que repo cada coisa vive.
