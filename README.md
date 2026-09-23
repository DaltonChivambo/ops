# MozaOps

Plataforma de automações operacionais do **Moza Banco** — Departamento de Meios de Pagamento
e Canais (DOP).

Substitui o fecho manual em Excel — exportar do Portal SIMO, do Banka e do MIS e cruzar à mão
com `VLOOKUP` — por execuções auditáveis e persistidas. Cada processo do departamento é uma
**automação**: um módulo com a sua página, as suas regras e as suas tabelas.

- **[`ARCHITECTURE.md`](ARCHITECTURE.md)** — o que o sistema é, e porquê: camadas, decomposição, infraestrutura.
- **[`OWNERS.md`](OWNERS.md)** — quem é dono de quê.

## Arquitectura, em cinco linhas

Monorepo. Backend FastAPI em workspace `uv`, com uma base de dados e um role por serviço, sem
acesso à do outro. Frontend Angular 22. Traefik como entrada única — o que faz com que o SPA e
a API partilhem origem e não exista CORS nenhum para configurar. Identidade no GEEA — o
Keycloak corporativo, já federado com o AD — e acesso por área, não por papel. Tudo em Docker
Compose.

## Estado

| | |
|---|---|
| [`platform/auth-service`](backend/services/platform/auth-service/README.md) | construído — sessões contra o GEEA, com as rotas das automações fechadas |
| Autenticação | ligada: credenciais do domínio, acesso por área |
| CI | por fazer |
| [`business/reconciliation/pos-closing-credit-validation`](backend/services/business/reconciliation/pos-closing-credit-validation/README.md) (POS) | construído — parse, reconciliação, persistência e relatório |
| Canais ATM e Quiosques | por fazer — serviços próprios, independentes do POS |
| Serviço `cases` | por fazer |

## Pré-requisitos

| | Versão | Notas |
|---|---|---|
| Docker | ≥ 25, com Compose v2 | traz o `uv` e o Python — não é preciso instalá-los |
| Node | ≥ 22.22.3 (usamos 24 LTS) | só para o frontend. O Angular 22 não instala com menos |

## Arrancar

Tudo a partir desta pasta (a raiz do repo — onde está este ficheiro, o
`docker-compose.yml` e o `.env.example`; não de dentro de `backend/` nem de
`frontend/`).

```bash
cp .env.example .env     # ajustar as senhas
make up                  # traefik, postgres, auth-service, otel, jaeger e os serviços
make migrate             # alembic upgrade head

# Em desenvolvimento o GEEA é simulado, e sobe à parte — não é um serviço nosso:
docker compose -f external-services/geea-keycloak/docker-compose.yml up -d
```

### Windows, sem `make`

O `Makefile` exige `bash` (`SHELL := /bin/bash`) — corre em Git Bash ou WSL. Em
PowerShell nativo, sem `make`, o equivalente é:

```powershell
Copy-Item .env.example .env      # ajustar as senhas
docker compose up -d --build     # traefik, postgres, auth-service, otel, jaeger e os serviços
docker compose run --rm pos-closing-credit-validation alembic upgrade head
docker compose -f external-services/geea-keycloak/docker-compose.yml up -d
```

Os passos seguintes (`make test`, `make down`, etc.) também têm equivalente
directo em `docker compose` — ver os alvos no [`Makefile`](Makefile) para o
comando exacto de cada um.

E o frontend, noutro terminal:

```bash
cd frontend && npm install && npm start   # http://localhost:4200
```

`*.localhost` resolve para 127.0.0.1 sem tocar no `/etc/hosts`:

| | |
|---|---|
| Aplicação (dev) | http://localhost:4200 |
| API (dev, direto) | http://localhost:8001 |
| GEEA (mock) | http://127.0.0.1:8100 |
| Jaeger | http://jaeger.mozaops.localhost |
| Painel do Traefik | http://127.0.0.1:8080 |

Para entrar, o mock do GEEA tem dois utilizadores, ambos com a password
`mude-me-em-producao`: `m001926` (Dalton Chivambo, abre todas as áreas) e
`m002000` (John Doe, só Canais). Quem é quem está em
[`external-services/geea-keycloak/README.md`](external-services/geea-keycloak/README.md).

```bash
make            # lista os comandos
make test       # testes do backend
make down       # pára, mantendo os dados
```

> **`make clean` apaga os volumes.** A base local pode ter execuções reais do departamento.
> Não é comando para correr por hábito.

## Convenções

**Tudo em inglês, excepto o que o operador lê.** Pastas, ficheiros, classes, funções,
variáveis de ambiente e tabelas são ingleses. Fica em português apenas o **conteúdo**: as
mensagens que o operador lê, os rótulos do relatório, os textos da interface e a documentação
— comentários incluídos. Nomes próprios não se traduzem: `SIMO`, `Banka`, `POS`, `eTicket`,
`MZN`.

As **rotas** são a excepção herdada: `/pos/validacao-credito-fecho` mantém os segmentos em
português do MozaOps v1, porque é o contrato que o frontend já consome.

## Aviso

Os ficheiros `.xlsx` do departamento são **dados bancários reais** e estão excluídos do
controlo de versões (`.gitignore`). Não os commitar, em circunstância nenhuma.
