SHELL := /bin/bash
.DEFAULT_GOAL := help

COMPOSE := docker compose

# O `lint` e o `test` partilham a imagem: é o estágio que traz o pytest, o ruff e
# o mypy, que a imagem de execução não leva. Construir uma vez serve os dois.
SERVICE := closing-credit-validation
CATEGORY := reconciliation
TEST_IMAGE := mozaops-$(SERVICE):test

.PHONY: help up down restart logs status verify-m0 psql clean migrate test lint test-image

help:  ## Mostra os comandos disponíveis
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

up:  ## Sobe a infraestrutura e os serviços
	@test -f .env || (echo "Falta o .env — copie o .env.example e ajuste." && exit 1)
	$(COMPOSE) up -d --build

migrate:  ## Aplica as migrações Alembic de cada serviço
	$(COMPOSE) run --rm closing-credit-validation alembic upgrade head

test-image:
	docker build --target test \
		--build-arg CATEGORY=$(CATEGORY) --build-arg SERVICE=$(SERVICE) \
		-t $(TEST_IMAGE) ./backend

test: test-image  ## Testes do backend (estágio `test` da imagem — a de execução não traz pytest)
	docker run --rm $(TEST_IMAGE)

lint: test-image  ## ruff (regras e formato) e mypy --strict, sobre o backend todo
	# O `cd /app` vai dentro do `sh` e não num `-w`: é em /app que está o
	# `pyproject.toml` com a configuração das duas ferramentas — e passá-lo em
	# `-w` faz o Git Bash do Windows traduzi-lo para um caminho que não existe.
	docker run --rm $(TEST_IMAGE) sh -c "cd /app && \
		ruff check . && \
		ruff format --check . && \
		mypy services/$(CATEGORY)/$(SERVICE)/app"

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
