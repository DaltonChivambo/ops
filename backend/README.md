# Backend

Serviços independentes e os pacotes internos que eles consomem. Ver [`../README.md`](../README.md)
para a arquitectura geral e como arrancar tudo, e [`services/README.md`](services/README.md)
para a organização por categoria e o que cada serviço tem de trazer.

## Estrutura

```
backend/
├── packages/       pacotes internos versionados, consumidos como wheel
└── services/       um serviço por automação — ver services/README.md
```

## Correr

A partir da raiz do monorepo — o backend não se arranca de dentro de `backend/`.
Se estiveres nesta pasta, sai primeiro: `cd ..`.

```bash
cp .env.example .env     # ajustar as senhas
make up                  # traefik, postgres, auth-service, otel, jaeger e os serviços
make migrate             # alembic upgrade head

# Em desenvolvimento o GEEA é simulado, e sobe à parte — não é um serviço nosso:
docker compose -f external-services/geea-keycloak/docker-compose.yml up -d
```

```bash
make            # lista os comandos
make check      # por pacote e serviço: lock, ruff, mypy --strict e pytest
make lock       # refaz o uv.lock e os requirements de cada serviço
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
| API | http://localhost:8101 |
| Rotas | `/api/pos/validacao-credito-fecho` |
| Docs (OpenAPI) | http://localhost:8101/docs |
| Health | http://localhost:8101/health |

Sem o `auth-service` nem o GEEA mock, as rotas protegidas por sessão devolvem 401 —
serve para ver o serviço a responder, não para testar o fluxo com autenticação.
Para isso, ou para o correr por completo com testes e lint, ver o
[README do serviço](services/business/reconciliation/pos-closing-credit-validation/README.md)
e a secção [«Correr»](#correr) acima.

## APIs

| Serviço | Categoria | Rotas | Porta (dev) |
|---|---|---|---|
| [`platform/auth-service`](services/platform/auth-service/README.md) | `platform` | `/api/auth-service` | 8010 |
| [`business/reconciliation/pos-closing-credit-validation`](services/business/reconciliation/pos-closing-credit-validation/README.md) | `business/reconciliation` | `/api/pos/validacao-credito-fecho` | 8101 |

Cada linha aponta para o README do serviço — o que faz, como se organiza, e como
correr só esse. Para subir tudo junto, ver o [«Arrancar» da raiz](../README.md#arrancar).

## Pacotes internos

`mozaops-libs` (em [`packages/mozaops-libs/`](packages/mozaops-libs/)): utilitários técnicos
partilhados entre serviços, hoje só a validação de tokens do GEEA (`mozaops_libs.auth`). Tem os
seus testes e o seu lock, e sai como wheel.

Nenhum serviço o lê por caminho. Cada um guarda em `wheels/` o wheel da versão que usa, e é
isso que o deixa actualizar ao seu ritmo:

```bash
ci/package.sh check  backend/packages/mozaops-libs
ci/package.sh vendor backend/packages/mozaops-libs backend/services/platform/auth-service
```

O `vendor` copia o wheel da versão actual, acerta o `pyproject.toml` do serviço e refaz o lock.

## Harbor, Nexus, GEEA e os outros endereços

Com Internet não se configura nada: as imagens vêm do Docker Hub, os pacotes do PyPI, e o GEEA
é o simulado. Na rede do banco, onde só o Harbor e o Nexus são alcançáveis, os endereços
metem-se **num só ficheiro, `ops/.env`**, a partir do `ops/.env.example`. Numa pipeline, as
mesmas variáveis vêm da configuração dela. Nunca nos Dockerfiles nem no código dos serviços.

| O quê | Variáveis no `ops/.env` | Quem usa |
|---|---|---|
| Harbor: imagem base do Python | `IMAGE_REGISTRY`, `IMAGE_NAMESPACE` | o `Dockerfile` de cada serviço, no build |
| Harbor: postgres, traefik, otel, jaeger | `IMAGE_REGISTRY`, `IMAGE_NAMESPACE` | o `docker-compose.yml` |
| Nexus: pacotes Python | `PYPI_INDEX_URL`, `PYPI_TRUSTED_HOST` | o `pip` do `Dockerfile` de cada serviço |
| GEEA: validar tokens | `AUTH_ISSUER`, `AUTH_JWKS_URL` | todos os serviços |
| GEEA: login | `GEEA_SSOLOGIN_URL`, `GEEA_TOKEN_URL`, `GEEA_REALM`, `GEEA_CLIENT_ID`, `GEEA_CLIENT_SECRET` | só o `auth-service` |
| GEEA: que cliente conta | `AUTH_ALLOWED_AZP`, `AUTH_CLIENT_ID` | todos os serviços |
| PostgreSQL | `POSTGRES_*`, `DB_*` | o `postgres` e as automações com base de dados |
| Harbor: publicar as imagens | `DOCKER_REGISTRY` | `ci/service.sh push` |
| Nexus: publicar o `mozaops-libs` | `PYPI_PUBLISH_URL` | `ci/package.sh publish` |

O que cada serviço lê em concreto está no README dele. O passo a passo para instalar numa
máquina da rede do banco, incluindo a troca para o GEEA do QAS, está no
[README da raiz](../README.md#instalar-no-computador-da-rede-do-banco).

**Uma coisa só se faz com Internet: mudar dependências Python.** O `ci/service.sh lock` precisa
do PyPI e recusa correr com `PYPI_INDEX_URL` definido.

## Dependências de um serviço

O `uv.lock` de cada serviço é a fonte. Dele saem o `requirements.txt` e o
`requirements-dev.txt`, com hashes, que são o que a imagem instala. Depois de mudar uma
dependência, ou para subir uma versão por causa de uma vulnerabilidade:

```bash
ci/service.sh lock <serviço>
UV_LOCK_ARGS="--upgrade-package pyjwt" ci/service.sh lock <serviço>
```

O uv corre num contentor, por isso não é preciso tê-lo instalado. Quem o tiver pode usar
`uv sync` e `uv run pytest` dentro da pasta do serviço, como em qualquer projecto Python.
