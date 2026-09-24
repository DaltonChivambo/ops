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

Serve para as duas máquinas: a que tem Internet e a da rede do banco, onde só o Harbor e o Nexus
são alcançáveis. Os passos que mudam dizem-no. O detalhe da rede do banco (as imagens que o
Harbor tem de ter, certificados, o GEEA do QAS) está em
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

O `.env` é o único ficheiro que muda entre máquinas. Há dois pontos de partida:

| | Máquina com Internet | Máquina na rede do banco |
|---|---|---|
| Ficheiro de partida | `.env.example` (está no git) | `.env.prod` (**não** está no git) |
| Imagens | Docker Hub | Harbor |
| Pacotes Python | PyPI | Nexus |
| GEEA | o simulado | o do QAS |

**Com Internet**, a partir do exemplo:

```bash
cp .env.example .env
```

Abrir o `.env` e trocar as senhas (`POSTGRES_PASSWORD`, `DB_*_PASSWORD`). O resto fica como vem.

**Na rede do banco**, a partir do `.env.prod`. Pede-se a quem mantém o MozaOps e copia-se para a
raiz do repositório por um canal interno. Depois:

```bash
cp .env.prod .env
```

E entrar no Harbor, uma vez por máquina, com o host que está em `IMAGE_REGISTRY`:

```bash
docker login <host do Harbor>
```

Antes de construir, confirmar que nenhuma imagem vem do Docker Hub:

```bash
docker compose config | grep image:   # todas começam pelo host do Harbor, excepto as mozaops/…:local
```

### 4. Backend

Igual nas duas máquinas:

```bash
make up          # constrói as imagens e sobe o postgres, o auth-service e a automação
make migrate     # cria as tabelas da automação (Alembic)
```

As dependências Python instalam-se **dentro das imagens**, a partir do `requirements.txt` de
cada serviço, no `make up`: do PyPI com Internet, do Nexus na rede do banco. Não há
`pip install` a fazer na máquina. A primeira vez demora uns minutos; as seguintes vêm da cache.

**Só com Internet**, o GEEA simulado, para se poder entrar sem o GEEA real:

```bash
docker compose -f external-services/geea-keycloak/docker-compose.yml --env-file .env up -d
```

Na rede do banco não se sobe: o `.env.prod` aponta ao GEEA do QAS.

Confirmar que está tudo de pé:

```bash
make status      # todos os contentores Up, e os serviços (healthy)
make verify-m0   # infraestrutura, isolamento das bases e login ponta a ponta
```

Na rede do banco, a parte «Identidade» do `verify-m0` falha: faz o login com os utilizadores do
GEEA simulado, que o GEEA do QAS não conhece. O resto tem de passar. O login verifica-se
entrando na aplicação com uma conta real.

### 5. Frontend

**Só na rede do banco**, uma vez por máquina, apontar o npm ao repositório npm do Nexus:

```bash
npm config set registry <URL do repositório npm do Nexus>
```

Depois, igual nas duas máquinas, noutro terminal:

```bash
cd frontend
npm ci           # instala as dependências exactamente como estão no package-lock.json
npm start        # http://localhost:4200
```

Abrir http://localhost:4200 e entrar:

- **com Internet**, com um dos utilizadores do GEEA simulado (as credenciais estão em
  [`external-services/geea-keycloak/README.md`](external-services/geea-keycloak/README.md));
- **na rede do banco**, com a conta do banco, a mesma do domínio.

O `npm start` encaminha o `/api` para o backend do passo 4, por isso os dois têm de estar de pé.

### 6. Testes

```bash
make check                          # backend: lock em dia, ruff, mypy --strict e pytest
cd frontend && npm test && npm run build   # frontend: testes unitários e build de produção
```

São os mesmos que o CI corre em cada push.

### 7. Parar, reinstalar e actualizar

Todos os comandos na raiz do repositório. Os de `docker compose` funcionam em qualquer
terminal, com ou sem `make`.

**Parar e voltar a subir**, mantendo os dados:

```bash
docker compose down        # pára e remove os contentores (make down)
docker compose up -d       # volta a subir (make up)
docker compose restart     # só reinicia, sem recriar
```

O GEEA simulado pára-se à parte:

```bash
docker compose -f external-services/geea-keycloak/docker-compose.yml down
```

**Depois de mudar o `.env`**, os contentores só lêem os valores novos se forem recriados:

```bash
docker compose up -d       # recria os que mudaram
```

**Reinstalar os contentores**, reconstruindo as imagens do zero e mantendo a base de dados.
Serve quando uma imagem ficou estragada ou se quer ter a certeza de que tudo vem de novo do
Harbor e do Nexus:

```bash
docker compose down
docker compose build --no-cache --pull
docker compose up -d
docker compose run --rm pos-closing-credit-validation alembic upgrade head
```

**Reinstalar tudo do zero, apagando a base de dados.** Apaga todas as execuções e casos:

```bash
docker compose down -v     # o -v apaga o volume da base (make clean)
docker compose up -d --build
docker compose run --rm pos-closing-credit-validation alembic upgrade head
```

> **O `-v` e o `make clean` apagam os dados.** A base local pode ter execuções reais do
> departamento. Não é comando para correr por hábito.

**Actualizar para código novo:**

```bash
git pull                   # ou descarregar de novo o ZIP do GitHub, e copiar o .env para lá
docker compose up -d --build
docker compose run --rm pos-closing-credit-validation alembic upgrade head   # se vieram migrações
cd frontend && npm ci      # se o package-lock.json mudou
```

**Ver o que se passa:**

```bash
docker compose ps                              # estado de cada contentor
docker compose logs -f auth-service            # log de um serviço, a seguir
docker logs mozaops-auth-service --tail 50     # as últimas 50 linhas
```

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

O Traefik (entrada única) e a observabilidade (collector e Jaeger) não são usados pelo código e
ficam desligados por omissão. Para os ligar:

```bash
docker compose --profile proxy up -d           # Traefik: http://mozaops.localhost, painel em http://127.0.0.1:8080
docker compose --profile observability up -d   # collector e Jaeger: http://jaeger.mozaops.localhost (precisa do proxy)
```

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
| Harbor: as imagens (Python e PostgreSQL) | `IMAGE_REGISTRY`, `IMAGE_NAMESPACE` |
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
| `postgres:18.6-trixie` | base de dados |

O Traefik, o collector e o Jaeger só são precisos se se ligarem os perfis `proxy` e
`observability`, que ficam desligados por omissão.

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

- **Com o `.env.prod`** (recomendado). Pede-se a quem mantém o MozaOps e leva-se para a máquina
  por um canal interno. Depois, na raiz do repositório:

  ```bash
  cp .env.prod .env
  ```

  Com o `.env.prod`, os passos 3 e 4 ficam feitos, e segue-se para o 5.

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
- Os contentores têm de chegar ao host do GEEA. O Windows completa um nome curto com o domínio
  da rede, mas os contentores não, e o login falha com «Não foi possível contactar o GEEA para
  validar as credenciais» (no log do `auth-service`: `SSOLogin inacessível: ConnectError`).
  Resolve-se dando o IP do host no mesmo `.env`, sem mexer nas quatro linhas:

  ```bash
  nslookup <host do GEEA do QAS>     # no Windows: mostra o IP
  ```

  ```bash
  GEEA_HOSTNAME=<host do GEEA do QAS, sem porta>
  GEEA_IP=<IP que o nslookup mostrou>
  ```

  Depois, `docker compose up -d` para os contentores lerem o `.env` novo.

  Se o Docker Desktop estiver configurado com o proxy do banco, os contentores já não o usam
  para o GEEA: o `GEEA_HOSTNAME` e o `GEEA_IP` entram sozinhos no `NO_PROXY` deles.

  Para ver de uma vez onde está o problema, na raiz do repositório:

  ```powershell
  powershell -ExecutionPolicy Bypass -File scripts\check-geea.ps1
  ```

  Confirma o `.env`, o que o compose lê, o que o contentor vê e se chega ao GEEA, e diz o que
  corrigir em cada passo que falhe.

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
