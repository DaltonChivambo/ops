SHELL := /bin/bash
.DEFAULT_GOAL := help

COMPOSE := docker compose

.PHONY: help up down restart logs status verify-m0 psql clean migrate test lint

help:  ## Mostra os comandos disponíveis
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

up:  ## Sobe a infraestrutura e os serviços
	@test -f .env || (echo "Falta o .env — copie o .env.example e ajuste." && exit 1)
	$(COMPOSE) up -d --build

migrate:  ## Aplica as migrações Alembic de cada serviço
	$(COMPOSE) run --rm closing-reconciliation alembic upgrade head

test:  ## Testes do backend (estágio `test` da imagem — a de execução não traz pytest)
	docker build --target test --build-arg SERVICE=closing-reconciliation \
		-t mozaops-closing-reconciliation:test ./backend
	docker run --rm mozaops-closing-reconciliation:test

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
