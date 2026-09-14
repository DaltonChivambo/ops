# Backend

Workspace `uv` com as bibliotecas partilhadas e os serviços. Ver [`../README.md`](../README.md)
para a arquitectura geral e como arrancar tudo, e [`services/README.md`](services/README.md)
para a organização por categoria e o que cada serviço tem de trazer.

## Estrutura

```
backend/
├── libs/           bibliotecas partilhadas entre serviços
└── services/       um serviço por automação — ver services/README.md
```

## Correr

A partir da raiz do monorepo — o backend não se arranca de dentro de `backend/`.
Se estiveres nesta pasta, sai primeiro: `cd ..`.

```bash
cp .env.example .env     # ajustar as senhas
make up                  # traefik, postgres, identity, otel, jaeger e os serviços
make migrate             # alembic upgrade head

# Em desenvolvimento o GEEA é simulado, e sobe à parte — não é um serviço nosso:
docker compose -f external-services/geea-keycloak/docker-compose.yml up -d
```

```bash
make            # lista os comandos
make test       # testes de todos os serviços, em contentor
make lint       # ruff (regras e formato) e mypy --strict, no workspace todo
make down       # pára, mantendo os dados
```

> **`make clean` apaga os volumes.** A base local pode ter execuções reais do
> departamento. Não é comando para correr por hábito.

Ver a tabela de portas em [«Arrancar» da raiz](../README.md#arrancar) para os
endereços em desenvolvimento, e o README de cada serviço abaixo para o correr
isoladamente.

### Só a primeira automação (reconciliação POS)

Para subir só o `pos-closing-credit-validation` — a primeira automação, sem os
outros serviços — a partir da raiz do monorepo (se estiveres nesta pasta, `cd ..`
primeiro):

```bash
cp .env.example .env                                          # se ainda não existir
docker compose up -d --build pos-closing-credit-validation    # traz o postgres consigo (depends_on)
docker compose run --rm pos-closing-credit-validation alembic upgrade head
```

| | |
|---|---|
| API | http://localhost:8001 |
| Rotas | `/api/pos/validacao-credito-fecho` |
| Docs (OpenAPI) | http://localhost:8001/docs |
| Health | http://localhost:8001/health |

Sem o `identity` nem o GEEA mock, as rotas protegidas por sessão devolvem 401 —
serve para ver o serviço a responder, não para testar o fluxo com autenticação.
Para isso, ou para o correr por completo com testes e lint, ver o
[README do serviço](services/business/reconciliation/pos-closing-credit-validation/README.md)
e a secção [«Correr»](#correr) acima.

## APIs

| Serviço | Categoria | Rotas | Porta (dev) |
|---|---|---|---|
| [`platform/identity`](services/platform/identity/README.md) | `platform` | `/api/identity` | 8002 |
| [`business/reconciliation/pos-closing-credit-validation`](services/business/reconciliation/pos-closing-credit-validation/README.md) | `business/reconciliation` | `/api/pos/validacao-credito-fecho` | 8001 |

Cada linha aponta para o README do serviço — o que faz, como se organiza, e como
correr só esse. Para subir tudo junto, ver o [«Arrancar» da raiz](../README.md#arrancar).

## `libs/`

`mozaops-libs` — utilitários técnicos partilhados entre serviços, hoje só a
validação de tokens do GEEA (`mozaops_libs.auth`). Resolvido a partir do
workspace e não do índice público (`tool.uv.package = false` no
[`pyproject.toml`](pyproject.toml) da raiz do backend).

## Workspace

O `uv` trata `libs` e cada serviço como membro do mesmo workspace
(`[tool.uv.workspace]` em [`pyproject.toml`](pyproject.toml)). Lint (`ruff`) e
tipagem (`mypy --strict`) configuram-se uma vez aqui e valem para todos os
membros — correm com `make lint` a partir da raiz do monorepo.
