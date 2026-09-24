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
| [`platform/auth-service`](backend/services/platform/auth-service/README.md) | construído — login contra o GEEA, sessões e acesso por área |
| [`business/reconciliation/pos-closing-credit-validation`](backend/services/business/reconciliation/pos-closing-credit-validation/README.md) (POS) | construído — leitura dos ficheiros, reconciliação, casos e relatório |
| Frontend | construído — Angular 22, com a página da automação POS |
| CI | GitHub Actions em cada push: backend (lock, ruff, mypy, pytest) e frontend (testes e build) |
| Canais ATM e Quiosques | por fazer — serviços próprios, independentes do POS |
| Traefik e observabilidade | configurados, mas desligados por omissão (não são usados pelo código) |

## Instalar e correr, do zero

Há duas máquinas possíveis, e os passos que mudam entre elas dizem-no:

| | Máquina com Internet | Máquina na rede do banco |
|---|---|---|
| Código | `git clone` | ZIP do GitHub (o proxy não deixa usar o `git`) |
| Terminal | qualquer, com ou sem `make` | PowerShell, sem `make` |
| Configuração | `.env.example` | `.env.prod` |
| Imagens | Docker Hub | Harbor |
| Pacotes Python | PyPI | Nexus |
| GEEA e Keycloak | o simulado (faz de ambos) | os do QAS |

Os comandos abaixo são de `docker compose`, que funcionam em qualquer terminal. O `make` é só
um atalho, onde existir.

### 1. Instalar as ferramentas

| Ferramenta | Versão | Onde | Para quê |
|---|---|---|---|
| **Docker Desktop** | Docker ≥ 25, Compose v2 | [docker.com](https://www.docker.com/products/docker-desktop/). No Windows, com o WSL 2 | o backend inteiro: Python, dependências e base de dados vêm nas imagens |
| **Node.js** | 24 LTS (aceita `^22.22.3`, `^24.15.0`, `>= 26`) | [nodejs.org](https://nodejs.org/), ou `nvm install 24` | só o frontend. O npm vem com ele |
| **Git** | qualquer recente | [git-scm.com](https://git-scm.com/downloads). No Windows traz o **Git Bash** | obter o código e correr os scripts `.sh`. Na rede do banco não é preciso |
| **make** | opcional | Linux e macOS já trazem | atalhos. Sem ele, ver [«Windows, sem `make`»](#windows-sem-make) |

Não é preciso instalar Python, `uv`, PostgreSQL nem o Angular CLI: o backend corre em
contentores, e o frontend usa o CLI local do projecto.

Confirmar, com o Docker Desktop aberto:

```bash
docker --version
docker compose version
node -v          # v24.x
npm -v
```

**Só na rede do banco**, antes de continuar, o Docker tem de confiar no certificado do Harbor e
ter sessão aberta nele. Ver os passos 1 e 2 de
[«Instalar no computador da rede do banco»](#instalar-no-computador-da-rede-do-banco).

### 2. Obter o código

**Com Internet:**

```bash
git clone https://github.com/DaltonChivambo/ops.git
cd ops
```

**Na rede do banco:** no GitHub, *Code → Download ZIP*, e descompactar. A pasta chama-se
`ops-main`, e o nome não importa: os contentores, a rede e a base de dados chamam-se sempre
`mozaops`.

Todos os comandos a seguir correm na raiz do projecto, a pasta do `docker-compose.yml`, salvo
quando dizem `cd frontend`.

### 3. Configurar

**Com Internet**, a partir do exemplo:

```bash
cp .env.example .env
```

Abrir o `.env` e trocar as senhas (`POSTGRES_PASSWORD`, `DB_*_PASSWORD`). O resto fica como vem.

**Na rede do banco**, a partir do `.env.prod`, que se pede a quem mantém o MozaOps e se copia
para a raiz do projecto por um canal interno:

```powershell
Copy-Item .env.prod .env
```

No Windows, confirmar que o ficheiro se chama mesmo `.env`, e não `.env.txt`:

```powershell
Get-ChildItem -Force .env*
```

### 4. Backend

```bash
docker compose up -d --build     # constrói as imagens e sobe o postgres, o auth-service e a automação (make up)
docker compose run --rm pos-closing-credit-validation alembic upgrade head   # cria as tabelas (make migrate)
```

As dependências Python instalam-se **dentro das imagens**, a partir do `requirements.txt` de
cada serviço: do PyPI com Internet, do Nexus na rede do banco. Não há `pip install` a fazer na
máquina. A primeira vez demora uns minutos; as seguintes vêm da cache.

**Só com Internet**, o GEEA simulado, para se poder entrar sem o GEEA real:

```bash
docker compose -f external-services/geea-keycloak/docker-compose.yml --env-file .env up -d
```

Confirmar que está tudo de pé:

```bash
docker compose ps        # o postgres, o auth-service e a automação Up (healthy)
```

- **Com Internet:** `make verify-m0` (ou `bash scripts/verify-m0.sh`) confirma a infraestrutura,
  o isolamento das bases e o login ponta a ponta.
- **Na rede do banco:** o diagnóstico da ligação ao GEEA, que é onde costuma falhar:

  ```powershell
  powershell -ExecutionPolicy Bypass -File scripts\check-geea.ps1
  ```

  Tem de acabar em «Tudo certo». Se não, diz o que corrigir.

### 5. Frontend

**Só na rede do banco**, uma vez por máquina, apontar o npm ao repositório npm do Nexus:

```bash
npm config set registry <URL do repositório npm do Nexus>
```

Depois, noutro terminal:

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

Na máquina com Internet:

```bash
make check                                  # backend: lock em dia, ruff, mypy --strict e pytest
cd frontend && npm test && npm run build    # frontend: testes unitários e build de produção
```

São os mesmos que o CI corre em cada push.

### 7. Parar, reinstalar e actualizar

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
docker compose up -d
```

**Reinstalar os contentores**, reconstruindo as imagens do zero e mantendo a base de dados:

```bash
docker compose down
docker compose build --no-cache
docker compose up -d
docker compose run --rm pos-closing-credit-validation alembic upgrade head
```

Sem `--pull`: com ele, o Docker volta a pedir a imagem base ao Harbor, e na rede do banco pode
falhar no certificado (ver [«Problemas comuns»](#problemas-comuns)).

**Reinstalar tudo do zero, apagando a base de dados.** Apaga todas as execuções e casos:

```bash
docker compose down -v     # o -v apaga o volume da base (make clean)
docker compose up -d --build
docker compose run --rm pos-closing-credit-validation alembic upgrade head
```

> **O `-v` e o `make clean` apagam os dados.** A base local pode ter execuções reais do
> departamento. Não é comando para correr por hábito.

**Actualizar para código novo:**

- **Com Internet:** `git pull`.
- **Na rede do banco:** descarregar o ZIP novo, descompactar, e copiar o `.env` da pasta antiga
  para a nova. Depois deixar de usar a pasta antiga: as duas controlariam os mesmos contentores.

E depois, nas duas:

```bash
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
| `make down` | `docker compose down` |
| `make clean` | `docker compose down -v` (apaga a base) |
| `make verify-m0` | `bash scripts/verify-m0.sh` (no Git Bash) |
| `make check` | `bash ci/service.sh check <pasta do serviço>` (no Git Bash) |

### Endereços em desenvolvimento

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

## Problemas comuns

| O que aparece | Porquê | O que fazer |
|---|---|---|
| `x509: certificate signed by unknown authority` ao construir | o Docker não confia no certificado do Harbor | passo 1 de [«Instalar no computador da rede do banco»](#instalar-no-computador-da-rede-do-banco); e construir sem `--pull` |
| «Não foi possível contactar o GEEA para validar as credenciais» | o contentor não chega ao GEEA ou ao Keycloak (no log: `SSOLogin inacessível: ConnectError`) | correr `scripts\check-geea.ps1` e seguir o que diz; quase sempre falta `GEEA_HOSTNAME`/`GEEA_IP` ou `KEYCLOAK_HOSTNAME`/`KEYCLOAK_IP` no `.env` |
| O login entra, mas as automações respondem 401 | o `AUTH_ISSUER` não é igual ao `iss` dos tokens | ler o `iss` de um token e pô-lo no `AUTH_ISSUER`, com o `AUTH_JWKS_URL` e o `GEEA_TOKEN_URL` do mesmo servidor |
| Mudei o `.env` e nada mudou | os contentores só lêem o `.env` quando são criados | `docker compose up -d` |
| O `npm ci` falha na rede do banco | o npm vai ao registo público | `npm config set registry <URL do repositório npm do Nexus>` |

## Onde se troca cada endereço

Nenhum endereço está escrito no código nem nos Dockerfiles. Tudo se troca no `.env`, a partir
do [`.env.example`](.env.example), ou nas variáveis da pipeline.

**Identidade.** São dois servidores: o **GEEA** faz o login, e o **Keycloak** emite, assina e
renova os tokens.

| Servidor | Para quê | Variáveis |
|---|---|---|
| GEEA | o login (recebe o utilizador e a password) | `GEEA_SSOLOGIN_URL`, `GEEA_REALM` |
| GEEA | o IP, quando o nome não resolve nos contentores | `GEEA_HOSTNAME`, `GEEA_IP` |
| Keycloak | quem emite os tokens (o `iss`) e onde estão as chaves | `AUTH_ISSUER`, `AUTH_JWKS_URL` |
| Keycloak | a renovação da sessão | `GEEA_TOKEN_URL` (tem GEEA no nome, mas é do Keycloak) |
| Keycloak | o IP, quando o nome não resolve nos contentores | `KEYCLOAK_HOSTNAME`, `KEYCLOAK_IP` |
| os dois | o cliente do MozaOps | `GEEA_CLIENT_ID`, `GEEA_CLIENT_SECRET`, `AUTH_ALLOWED_AZP`, `AUTH_CLIENT_ID` |

**O resto:**

| O quê | Variáveis |
|---|---|
| Harbor: as imagens (Python e PostgreSQL) | `IMAGE_REGISTRY`, `IMAGE_NAMESPACE` |
| Nexus: os pacotes Python | `PYPI_INDEX_URL`, e `PYPI_TRUSTED_HOST` se servir em HTTP |
| PostgreSQL | `POSTGRES_*`, `DB_*` |
| Harbor: para onde vai a imagem construída | `DOCKER_REGISTRY` (só para publicar) |
| Nexus: onde se publica o `mozaops-libs` | `PYPI_PUBLISH_URL` (só para publicar) |

### Instalar no computador da rede do banco

O que é próprio da rede do banco, em complemento de [«Instalar e correr, do
zero»](#instalar-e-correr-do-zero). Os valores entre `<>` são os do banco, e não estão escritos
no repositório.

**1. O Docker confiar no Harbor.** O Harbor usa um certificado da CA interna do banco. Uma de
duas, no Docker Desktop:

- instalar no Windows o certificado raiz do banco, em *Autoridades de Certificação de Raiz
  Fidedignas*, e reiniciar o Docker Desktop (recomendado);
- ou *Settings → Docker Engine*, acrescentar ao JSON
  `"insecure-registries": ["<host do Harbor>"]`, e *Apply & restart*.

**2. Entrar no Harbor**, uma vez por máquina, e confirmar que as imagens base estão lá:

```powershell
docker login <host do Harbor>
docker pull <host do Harbor>/<projecto>/python:3.14-slim-trixie
docker pull <host do Harbor>/<projecto>/postgres:18.6-trixie
```

São as duas únicas imagens de que o `docker compose up` precisa. O Traefik, o collector e o
Jaeger só com os perfis `proxy` e `observability`.

**3. O `.env`.** O `.env.prod` já vem preparado para a rede do banco. Sem ele, parte-se do
`.env.example` e preenche-se:

- a secção «De onde vêm as imagens e os pacotes»: `IMAGE_REGISTRY`, `IMAGE_NAMESPACE`,
  `PYPI_INDEX_URL` e `PYPI_TRUSTED_HOST`;
- as senhas;
- o GEEA do QAS, como no ponto 4.

**4. O GEEA e o Keycloak do QAS.** No bloco «Identidade» do `.env`, comentar as quatro linhas
do simulado e descomentar as do QAS:

```bash
GEEA_SSOLOGIN_URL=http://<host do GEEA>/geea/idmUtils/SSOLogin
AUTH_ISSUER=http://<host do Keycloak>/auth/realms/QAS
AUTH_JWKS_URL=http://<host do Keycloak>/auth/realms/QAS/protocol/openid-connect/certs
GEEA_TOKEN_URL=http://<host do Keycloak>/auth/realms/QAS/protocol/openid-connect/token
GEEA_CLIENT_SECRET=<segredo do qa-mozaops>
```

O GEEA (o login) e o Keycloak (os tokens) estão em servidores diferentes. O do Keycloak é o do
campo `iss` de um token: tira-se um pelo Postman, com o mesmo pedido de login ao GEEA, e lê-se o
`iss`.
O `AUTH_ISSUER` é esse valor, tal e qual.

Os contentores não resolvem os nomes curtos dos servidores, que o Windows completa com o
domínio da rede. Dá-se-lhes o IP de cada um, que o `ping <host>` mostra na primeira linha:

```bash
GEEA_HOSTNAME=<host do GEEA, sem porta>
GEEA_IP=<IP dele>
KEYCLOAK_HOSTNAME=<host do Keycloak, sem porta>
KEYCLOAK_IP=<IP dele>
```

Estes nomes também entram sozinhos no `NO_PROXY` dos contentores, para o proxy do banco não se
meter pelo meio. Depois de mudar o `.env`, `docker compose up -d`, e confirmar com
`scripts\check-geea.ps1`.

Com o GEEA do QAS, o simulado não se sobe. O `verify-m0` também não serve aqui: faz o login com
os utilizadores do simulado.

**O que não se faz nesta máquina:** mudar dependências Python (`ci/service.sh lock`). Precisa do
PyPI, e recusa correr com `PYPI_INDEX_URL` definido. Faz-se na máquina com Internet, faz-se
commit do `uv.lock` e dos `requirements*.txt`, e esta máquina instala-os pelo Nexus.
