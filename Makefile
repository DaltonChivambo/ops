SHELL := /bin/bash
.DEFAULT_GOAL := help

COMPOSE := docker compose

# Os serviços e os pacotes descobrem-se pela pasta: um serviço novo não obriga a
# editar este ficheiro. Para correr só um:
# `make check SERVICES=backend/services/platform/auth-service`.
SERVICES ?= $(patsubst %/Dockerfile,%,$(wildcard backend/services/*/*/Dockerfile backend/services/*/*/*/Dockerfile))
PACKAGES ?= $(patsubst %/pyproject.toml,%,$(wildcard backend/packages/*/pyproject.toml))

.PHONY: help up down restart logs status verify-m0 psql clean migrate check build lock

help:  ## Mostra os comandos disponíveis
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

up:  ## Sobe a infraestrutura e os serviços
	@test -f .env || (echo "Falta o .env — copie o .env.example e ajuste." && exit 1)
	$(COMPOSE) up -d --build

migrate:  ## Aplica as migrações Alembic de cada serviço
	$(COMPOSE) run --rm pos-closing-credit-validation alembic upgrade head

check:  ## Lock em dia, ruff, mypy e pytest, em cada pacote e serviço
	@for dir in $(PACKAGES); do ci/package.sh check $$dir || exit 1; done
	@for dir in $(SERVICES); do ci/service.sh check $$dir || exit 1; done

build:  ## Imagens de execução de todos os serviços
	@for dir in $(SERVICES); do ci/service.sh build $$dir || exit 1; done

lock:  ## Refaz o uv.lock e os requirements de cada serviço
	@for dir in $(SERVICES); do ci/service.sh lock $$dir || exit 1; done

down:  ## Pára tudo, mantendo os dados
	$(COMPOSE) down

restart:  ## Pára e volta a subir
	$(COMPOSE) down && $(COMPOSE) up -d

logs:  ## Segue os logs de todos os containers
	$(COMPOSE) logs -f

status:  ## Estado dos containers
	$(COMPOSE) ps

psql:  ## Abre o psql como superutilizador
	$(COMPOSE) exec postgres psql -U $${POSTGRES_USER:-postgres}

clean:  ## APAGA os volumes — bases e realm voltam ao zero
	$(COMPOSE) down -v

verify-m0:  ## Critério de «feito» do M0: infraestrutura de pé e autenticável
	@bash scripts/verify-m0.sh
