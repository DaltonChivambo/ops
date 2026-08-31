# Atalhos do monorepo. Todos os builds usam contexto na raiz (ver ADR 0005).
COMPOSE := docker compose -f infra/compose/docker-compose.yml -f infra/compose/docker-compose.override.yml
INFRA   := docker compose -f infra/compose/docker-compose.infra.yml

.PHONY: infra-up infra-down up down build logs ps migrate registry test lint keys

keys:            ## gera o par RS256 usado pelo Auth Service (dev)
	@mkdir -p infra/compose/keys
	openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out infra/compose/keys/jwt-private.pem
	openssl rsa -pubout -in infra/compose/keys/jwt-private.pem -out infra/compose/keys/jwt-public.pem

infra-up:        ## passo 01 do roadmap: infra de pé, sem codigo aplicacional
	$(INFRA) up -d

infra-down:
	$(INFRA) down

up: infra-up
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down

build:
	$(COMPOSE) build

logs:
	$(COMPOSE) logs -f --tail=100

ps:
	$(COMPOSE) ps

migrate:         ## alembic upgrade head em todos os serviços
	@for s in auth ticketing asset approval notification reporting; do \
		echo "== $$s"; $(COMPOSE) run --rm $$s alembic upgrade head; \
	done

registry:        ## regenera docs/registry.md a partir dos service.yaml
	python scripts/gen_registry.py

test:
	@for s in auth ticketing asset approval notification reporting; do \
		echo "== $$s"; (cd backend/services/$$s && python -m pytest -q) || exit 1; \
	done

lint:
	ruff check backend/
