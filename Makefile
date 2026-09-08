SHELL := /bin/bash
.DEFAULT_GOAL := help

COMPOSE := docker compose

# O `lint` e o `test` partilham a imagem: é o estágio que traz o pytest, o ruff e
# o mypy, que a imagem de execução não leva. Construir uma vez serve os dois.
#
# `SERVICES` é a lista `categoria/serviço`. Estava aqui um serviço fixo, e com o
# segundo isso deixava metade do backend por testar sem o dizer. Para correr só
# um: `make test SERVICES=platform/identity`.
SERVICES := reconciliation/closing-credit-validation platform/identity

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
	@for path in $(SERVICES); do \
		category=$${path%%/*}; service=$${path##*/}; \
		docker build --target test \
			--build-arg CATEGORY=$$category --build-arg SERVICE=$$service \
			-t mozaops-$$service:test ./backend || exit 1; \
	done

test: test-image  ## Testes do backend (estágio `test` da imagem — a de execução não traz pytest)
	@for path in $(SERVICES); do \
		service=$${path##*/}; \
		echo "── $$service ─────────────────────────────────────────────"; \
		docker run --rm mozaops-$$service:test || exit 1; \
	done
	@# A lib partilhada tem testes próprios e nenhum serviço os corre: os
	@# `pytest` de cada serviço param na pasta dele. Correm-se na imagem de um
	@# deles, que já traz o workspace instalado.
	@#
	@# O `cd` vai dentro do `sh` e não num `-w`, pela mesma razão que no `lint`:
	@# o Git Bash do Windows traduz o caminho do `-w` e o container recebe algo
	@# como `C:/Program Files/Git/app/libs`.
	@echo "── mozaops-libs ──────────────────────────────────────────"
	@docker run --rm mozaops-identity:test sh -c "cd /app/libs && pytest -q"

lint: test-image  ## ruff (regras e formato) e mypy --strict, sobre o backend todo
	@# Uma passagem por serviço, e não uma só: a imagem de cada um traz o seu
	@# código e a `libs/`, mas não o código dos outros — é o preço de o
	@# contexto de build ser estreito, e correr só numa deixava metade por
	@# olhar sem o dizer.
	@#
	@# O `cd /app` vai dentro do `sh` e não num `-w`: é em /app que está o
	@# `pyproject.toml` com a configuração das duas ferramentas — e passá-lo em
	@# `-w` faz o Git Bash do Windows traduzi-lo para um caminho que não existe.
	@for path in $(SERVICES); do \
		category=$${path%%/*}; service=$${path##*/}; \
		echo "── $$service ─────────────────────────────────────────────"; \
		docker run --rm mozaops-$$service:test sh -c "cd /app && \
			ruff check . && \
			ruff format --check . && \
			mypy libs/src/mozaops_libs services/$$category/$$service/app" || exit 1; \
	done

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
