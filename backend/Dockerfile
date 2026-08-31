# syntax=docker/dockerfile:1

# A imagem de qualquer um dos serviços FastAPI.
#
# ────────────────────────────────────────────────────────────────────────────
# AINDA NÃO CONSTRÓI. `services/closing-reconciliation/` e `services/cases/`
# são pastas vazias: não há `pyproject.toml` de serviço, não há `uv.lock`, não
# há `app/`. Isto é o padrão que o M1 vai preencher, escrito à frente para que
# a forma da imagem seja uma decisão tomada e não uma pressa no fim.
# ────────────────────────────────────────────────────────────────────────────
#
# **Um Dockerfile para os dois serviços, e não um por serviço** — desvio ao que
# o docs/implementation-plan.md:384 previa, com uma razão concreta: o
# `backend/pyproject.toml` declara um workspace uv cujos membros são `libs` e
# `services/*`, e as libs são dependências por caminho. Qualquer serviço só
# resolve com a raiz do workspace e `libs/` presentes, o que obriga o contexto
# de build a ser `backend/` — e nesse ponto dois ficheiros idênticos dentro das
# pastas dos serviços seriam duplicação a ter de andar sincronizada. O que
# muda entre eles é o nome; passa em `--build-arg`.
#
#   docker build --build-arg SERVICE=closing-reconciliation -t mozaops-closing backend
#   docker build --build-arg SERVICE=cases                  -t mozaops-cases   backend

ARG SERVICE

# ─── Dependências ─────────────────────────────────────────────────────────────
# O uv vem por COPY de uma imagem própria em vez de `pip install uv`: é um
# binário estático, não precisa de entrar no ambiente Python que vai correr em
# produção, e a versão fica visível numa linha em vez de escondida num lock.
# A tag é a mesma que os postos de trabalho usam — se divergirem, o lock
# resolve-se de uma maneira na máquina de quem desenvolve e de outra no build.
FROM ghcr.io/astral-sh/uv:0.12.1 AS uv

FROM python:3.12-slim AS build
ARG SERVICE

COPY --from=uv /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Os manifestos antes do código. Enquanto as dependências não mudarem, a camada
# pesada — instalar tudo — vem da cache, e mexer numa rota não obriga a
# reinstalar o SQLAlchemy.
#
# `--no-install-workspace` instala as dependências mas não os pacotes do próprio
# workspace, que é o que permite esta separação em dois passos.
COPY pyproject.toml uv.lock ./
COPY libs/ libs/
COPY services/${SERVICE}/pyproject.toml services/${SERVICE}/
RUN uv sync --locked --no-dev --no-install-workspace --package mozaops-${SERVICE}

# Agora o código, e o segundo sync só instala os pacotes do workspace.
COPY services/${SERVICE}/ services/${SERVICE}/
RUN uv sync --locked --no-dev --package mozaops-${SERVICE}

# ─── Testes ───────────────────────────────────────────────────────────────────
# Estágio à parte porque a imagem de execução é `--no-dev`: o pytest não entra
# no que vai para produção. Não é alcançado por um build normal — só com
# `--target test`, que é o que o `make test` faz.
FROM build AS test
ARG SERVICE
RUN uv sync --locked --package mozaops-${SERVICE}
# O PATH do .venv só é posto no estágio de execução; aqui é preciso repeti-lo.
ENV PATH="/app/.venv/bin:$PATH"
WORKDIR /app/services/${SERVICE}
CMD ["pytest", "-q"]

# ─── Execução ─────────────────────────────────────────────────────────────────
# Sem uv, sem compilador, sem manifestos: só o interpretador e o .venv já
# resolvido. `--locked` acima garante que o build falha se o lock estiver
# desactualizado, em vez de resolver versões diferentes das que foram testadas.
FROM python:3.12-slim AS runtime
ARG SERVICE

# Não-root. Um uid fixo e não o que a distribuição decidir: quando houver
# volumes montados, as permissões têm de ser previsíveis entre máquinas.
RUN useradd --system --uid 1001 --user-group --no-create-home app

WORKDIR /app
COPY --from=build --chown=app:app /app /app

# O .venv à frente do PATH dispensa `uv run` em produção — o `gunicorn` e o
# `alembic` do ambiente são os que se invocam, sem camada nenhuma pelo meio.
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# É daqui que `app.main:app` e `alembic.ini` são caminhos relativos válidos.
WORKDIR /app/services/${SERVICE}

USER app
EXPOSE 8000

# A imagem não traz curl — instalá-lo por causa do healthcheck seria pagar uma
# dependência e uma superfície de ataque por três segundos de arranque. O
# interpretador já lá está e chega.
HEALTHCHECK --interval=10s --timeout=3s --retries=5 --start-period=10s \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)"

# Gunicorn a gerir workers uvicorn: o uvicorn sozinho não repõe um worker que
# morra, e num processo que lê Excel de vários MB isso não é hipótese teórica.
#
# O processo de fundo (`app/worker.py`, que drena a fila de execuções) corre
# nesta mesma imagem com outro comando — é o mesmo código e as mesmas
# dependências, e duas imagens divergiriam sem ninguém dar por isso:
#
#   command: ["python", "-m", "app.worker"]
CMD ["gunicorn", "app.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "2", \
     "--bind", "0.0.0.0:8000", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--graceful-timeout", "30", \
     "--timeout", "60"]
