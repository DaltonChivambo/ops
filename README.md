# MozaOps

Plataforma de automação de processos operacionais do **Moza Banco**, para a **Direcção de
Operações**.

Leva para um só sítio o trabalho que hoje se faz à mão em folhas de cálculo: cruzar ficheiros
de vários sistemas, encontrar o que não bate e acompanhar cada caso até ficar resolvido. Cada
processo passa a ser uma **automação**, com a sua página e as suas regras. Cada execução fica
gravada, com o relatório e os casos por tratar, e cada pessoa entra com a conta do banco e vê
só as áreas em que trabalha.

A primeira automação é a validação de crédito de valores de fecho de POS, do departamento de
Meios de Pagamento e Canais.

- **[`ARCHITECTURE.md`](ARCHITECTURE.md)** — o que o sistema é, e porquê: camadas, decomposição, infraestrutura.
- **[`OWNERS.md`](OWNERS.md)** — quem é dono de quê.

## Estado

| | |
|---|---|
| [`platform/auth-service`](backend/services/platform/auth-service/README.md) | construído — sessões contra o GEEA, com as rotas das automações fechadas |
| Autenticação | ligada: credenciais do domínio, acesso por área |
| CI | por fazer |
| [`business/reconciliation/pos-closing-credit-validation`](backend/services/business/reconciliation/pos-closing-credit-validation/README.md) (POS) | construído — parse, reconciliação, persistência e relatório |
| Canais ATM e Quiosques | por fazer — serviços próprios, independentes do POS |
| Serviço `cases` | por fazer |

## Instalar e correr, do zero

Numa máquina com Internet. Numa máquina da rede do banco, fazer primeiro os passos de
[«Instalar no computador da rede do banco»](#instalar-no-computador-da-rede-do-banco).

### 1. Instalar as ferramentas

| Ferramenta | Versão | Onde | Para quê |
|---|---|---|---|
| **Git** | qualquer recente | [git-scm.com](https://git-scm.com/downloads). No Windows traz o **Git Bash** | obter o código, e o `bash` dos scripts |
| **Docker Desktop** | Docker ≥ 25, Compose v2 | [docker.com](https://www.docker.com/products/docker-desktop/). No Windows, com o WSL 2 | o backend inteiro: Python, dependências e base de dados vêm nas imagens |
| **Node.js** | 24 LTS (aceita `^22.22.3`, `^24.15.0`, `>= 26`) | [nodejs.org](https://nodejs.org/), ou `nvm install 24` | só o frontend. O npm vem com ele |
| **make** | opcional | Linux e macOS já trazem. No Windows, usar os comandos de [«Windows, sem `make`»](#windows-sem-make) | atalhos para os comandos abaixo |

Não é preciso instalar Python, `uv`, PostgreSQL nem o Angular CLI: o backend corre em
contentores, e o frontend usa o CLI local do projecto.

Confirmar:

```bash
git --version
docker --version && docker compose version
node -v          # v24.x
npm -v
```

O Docker Desktop tem de estar aberto antes dos passos seguintes.

### 2. Obter o código

```bash
git clone https://github.com/DaltonChivambo/ops.git
cd ops
```

Todos os comandos a seguir correm desta pasta, a raiz do repositório, salvo quando dizem
`cd frontend`.

### 3. Configurar

```bash
cp .env.example .env
```

Abrir o `.env` e trocar as senhas (`POSTGRES_PASSWORD`, `DB_*_PASSWORD`). Para desenvolvimento,
o resto pode ficar como vem: o GEEA simulado, e tudo da Internet.

### 4. Backend

```bash
make up          # constrói as imagens e sobe traefik, postgres, auth-service, a automação, otel e jaeger
make migrate     # cria as tabelas da automação (Alembic)
```

As dependências Python instalam-se **dentro das imagens**, a partir do `requirements.txt` de
cada serviço, no `make up`. Não há `pip install` a fazer na máquina. A primeira vez demora uns
minutos; as seguintes vêm da cache.

O GEEA simulado, para se poder entrar sem o GEEA real:

```bash
docker compose -f external-services/geea-keycloak/docker-compose.yml --env-file .env up -d
```

Confirmar que está tudo de pé:

```bash
make status      # todos os contentores Up, e os serviços (healthy)
make verify-m0   # infraestrutura, isolamento das bases e login ponta a ponta
```

### 5. Frontend

Noutro terminal:

```bash
cd frontend
npm ci           # instala as dependências exactamente como estão no package-lock.json
npm start        # http://localhost:4200
```

Abrir http://localhost:4200 e entrar com um dos utilizadores do GEEA simulado (as credenciais
estão em [`external-services/geea-keycloak/README.md`](external-services/geea-keycloak/README.md)).
O `npm start` encaminha o `/api` para o backend do passo 4, por isso os dois têm de estar de pé.

### 6. Testes

```bash
make check                          # backend: lock em dia, ruff, mypy --strict e pytest
cd frontend && npm test && npm run build   # frontend: testes unitários e build de produção
```

São os mesmos que o CI corre em cada push.

### 7. Parar e actualizar

```bash
make down        # pára tudo, mantendo os dados
git pull         # código novo
make up          # reconstrói o que mudou
make migrate     # se vieram migrações novas
cd frontend && npm ci   # se o package-lock.json mudou
```

> **`make clean` apaga os volumes.** A base local pode ter execuções reais do departamento.
> Não é comando para correr por hábito.

### Windows, sem `make`

O `Makefile` exige `bash`, que corre em Git Bash ou WSL. Em PowerShell, os equivalentes:

| Com `make` | Sem `make` |
|---|---|
| `cp .env.example .env` | `Copy-Item .env.example .env` |
| `make up` | `docker compose up -d --build` |
| `make migrate` | `docker compose run --rm pos-closing-credit-validation alembic upgrade head` |
| `make status` | `docker compose ps` |
| `make verify-m0` | `bash scripts/verify-m0.sh` (no Git Bash) |
| `make check` | `bash ci/service.sh check <pasta do serviço>` (no Git Bash) |
| `make down` | `docker compose down` |

### Endereços em desenvolvimento

`*.localhost` resolve para 127.0.0.1 sem tocar no `/etc/hosts`.

| | |
|---|---|
| Aplicação | http://localhost:4200 |
| API da automação POS | http://localhost:8101 (docs em `/docs`) |
| API do `auth-service` | http://localhost:8010 |
| GEEA simulado | http://127.0.0.1:8100 |
| Jaeger | http://jaeger.mozaops.localhost |
| Painel do Traefik | http://127.0.0.1:8080 |

## Onde se troca cada endereço

Nenhum endereço está escrito no código nem nos Dockerfiles. Mudam de host, de IP e de porta,
e cada um tem um só sítio onde se troca.

**A aplicação** (`.env`, a partir do [`.env.example`](.env.example)):

| O quê | Variáveis |
|---|---|
| GEEA: quem emite os tokens | `AUTH_ISSUER`, `AUTH_JWKS_URL` |
| GEEA: login e troca de credenciais | `GEEA_SSOLOGIN_URL`, `GEEA_TOKEN_URL`, `GEEA_REALM` |
| GEEA: o cliente do MozaOps | `GEEA_CLIENT_ID`, `GEEA_CLIENT_SECRET`, `AUTH_ALLOWED_AZP`, `AUTH_CLIENT_ID` |
| Domínio público | `DOMAIN` |
| PostgreSQL | `POSTGRES_*`, `DB_*` |

O `.env.example` traz o GEEA simulado activo e, comentadas por baixo, as mesmas linhas para o
GEEA do QAS. Trocar de um para o outro é trocar esse bloco. O `AUTH_ISSUER` tem de
acompanhar, porque é contra ele que se valida o `iss` de cada token.

**De onde vêm as imagens e os pacotes** (também no `.env`):

| O quê | Variáveis |
|---|---|
| Harbor: todas as imagens (Python, postgres, traefik, otel, jaeger) | `IMAGE_REGISTRY`, `IMAGE_NAMESPACE` |
| Nexus: os pacotes Python | `PYPI_INDEX_URL`, e `PYPI_TRUSTED_HOST` se servir em HTTP |
| Harbor: para onde vai a imagem construída | `DOCKER_REGISTRY` |
| Nexus: onde se publica o `mozaops-libs` | `PYPI_PUBLISH_URL` |
| Harbor: imagem do uv, para o `mozaops-libs` | `UV_IMAGE` |

As duas primeiras linhas são as que decidem a máquina. As outras três só servem para publicar.

### Instalar no computador da rede do banco

Passo a passo, numa máquina que só chega ao Harbor e ao Nexus. Os valores entre `<>` são os do
banco, e não estão escritos no repositório.

**1. Confirmar que o Harbor tem as imagens.** Todas no mesmo projecto, com estes nomes e tags:

| Imagem | Para quê |
|---|---|
| `python:3.14-slim-trixie` | base dos serviços e do GEEA simulado |
| `postgres:18-alpine` | base de dados |
| `traefik:v3.6` | entrada |
| `opentelemetry-collector-contrib:0.144.0` | observabilidade |
| `jaeger:2.12.0` | observabilidade |

Se alguma tiver outro nome no Harbor, é esse o nome a pedir que se espelhe, ou a mudar no
`docker-compose.yml`.

**2. Entrar no Harbor.** Uma vez por máquina:

```bash
docker login <host do Harbor>
```

Se o Harbor usar um certificado da CA interna, o Docker tem de confiar nela primeiro. No
Docker Desktop: *Settings → Docker Engine*, e acrescentar o host a `insecure-registries`, ou
instalar a CA no Windows.

**3. Criar o `.env`.** Há duas maneiras:

- **Com o `.env.prod`** (recomendado). É um ficheiro com os endereços reais do Harbor, do Nexus
  e do GEEA do QAS já preenchidos. **Não está no git**, porque tem endereços internos do banco:
  pede-se a quem mantém o MozaOps e leva-se para a máquina por um canal interno. Depois, na raiz
  do repositório:

  ```bash
  cp .env.prod .env
  ```

  Faltam só os valores entre `<>`: as senhas e o `GEEA_CLIENT_SECRET`. Com o `.env.prod`, os
  passos 3 e 4 ficam feitos, e segue-se para o 5.

- **À mão**, a partir do modelo, preenchendo a secção «De onde vêm as imagens e os pacotes»:

```bash
cp .env.example .env
```

```bash
IMAGE_REGISTRY=<host do Harbor>
IMAGE_NAMESPACE=<projecto do Harbor>
PYPI_INDEX_URL=<URL do Nexus, terminado em /simple/>
PYPI_TRUSTED_HOST=<host do Nexus>        # só se o Nexus servir em HTTP
```

No mesmo `.env`, trocar as senhas.

**4. Apontar ao GEEA do QAS**, em vez do simulado. Tudo no mesmo ficheiro,
`ops/.env`, na secção «GEEA»:

1. Comentar as quatro linhas do simulado:
   ```bash
   # AUTH_ISSUER=http://geea-keycloak:8000/auth/realms/QAS
   # AUTH_JWKS_URL=http://geea-keycloak:8000/auth/realms/QAS/protocol/openid-connect/certs
   # GEEA_SSOLOGIN_URL=http://geea-keycloak:8000/geea/idmUtils/SSOLogin
   # GEEA_TOKEN_URL=http://geea-keycloak:8000/auth/realms/QAS/protocol/openid-connect/token
   ```
2. Descomentar as quatro do QAS, logo abaixo, e pôr o host do GEEA do QAS:
   ```bash
   AUTH_ISSUER=http://<host do GEEA do QAS>/auth/realms/QAS
   AUTH_JWKS_URL=http://<host do GEEA do QAS>/auth/realms/QAS/protocol/openid-connect/certs
   GEEA_SSOLOGIN_URL=http://<host do GEEA do QAS>/geea/idmUtils/SSOLogin
   GEEA_TOKEN_URL=http://<host do GEEA do QAS>/auth/realms/QAS/protocol/openid-connect/token
   ```
3. Pôr o segredo real do cliente, pedido a quem gere o GEEA:
   ```bash
   GEEA_CLIENT_SECRET=<segredo do qa-mozaops>
   ```
   `GEEA_REALM`, `GEEA_CLIENT_ID`, `AUTH_ALLOWED_AZP` e `AUTH_CLIENT_ID` ficam como estão.

Dois cuidados:
- O `AUTH_ISSUER` tem de ser igual ao `iss` dos tokens do QAS. Se não for, o login entra mas
  as automações respondem 401.
- Os contentores têm de chegar ao host do GEEA. Se o nome curto não resolver dentro do Docker,
  usar o nome completo, com o domínio, nas quatro linhas.

Com o GEEA do QAS, o simulado não se sobe.

**5. Confirmar de onde vem cada imagem**, antes de construir:

```bash
docker compose config | grep image:
```

Todas têm de começar pelo host do Harbor, excepto as `mozaops/…:local`, que são construídas
na própria máquina.

**6. Subir tudo:**

```bash
make up
make migrate
# GEEA simulado, só se não se usar o do QAS:
docker compose -f external-services/geea-keycloak/docker-compose.yml --env-file .env up -d
make verify-m0
```

Sem `make`, os mesmos comandos estão em [«Windows, sem `make`»](#windows-sem-make).

**7. Frontend.** O `npm` também tem de ir ao Nexus, a um repositório npm. Configura-se na
máquina, e não no repositório:

```bash
npm config set registry <URL do repositório npm do Nexus>
cd frontend && npm ci && npm start
```

Se o Nexus não tiver repositório npm, o frontend corre numa máquina com Internet.

**O que não se faz nesta máquina:** mudar dependências Python (`ci/service.sh lock`). Precisa do
PyPI, e recusa correr com `PYPI_INDEX_URL` definido. Faz-se na máquina com Internet, faz-se
commit do `uv.lock` e dos `requirements*.txt`, e esta máquina instala-os pelo Nexus.
