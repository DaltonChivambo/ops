# A imagem deste serviço, e só dele: o contexto de build é esta pasta.
#
#   docker build -t auth-service:local .
#   docker build --target test -t auth-service:test . && \
#     docker run --rm auth-service:test
#
# Sem argumentos, tudo vem da Internet: a imagem base do Docker Hub e os pacotes
# do PyPI. Na rede do banco os ARG apontam ao Harbor e ao Nexus, os únicos
# alcançáveis, e nada neste ficheiro muda.

# De onde vem a imagem base: o registo, o projecto dentro dele, e a imagem.
# O valor de PYTHON_IMAGE é a versão do Python deste serviço, igual ao
# `requires-python` do pyproject.toml. Sobrepõe-se só quando o Harbor dá
# outro nome à mesma versão; mudar de versão é mudar os dois aqui.
ARG IMAGE_REGISTRY=docker.io
ARG IMAGE_NAMESPACE=library
ARG PYTHON_IMAGE=python:3.14-slim-trixie

FROM ${IMAGE_REGISTRY}/${IMAGE_NAMESPACE}/${PYTHON_IMAGE} AS base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/opt/venv/bin:$PATH"
WORKDIR /app

# ─── Dependências ─────────────────────────────────────────────────────────────
# O `requirements.txt` sai do `uv.lock` com os hashes de cada ficheiro. São os
# mesmos no PyPI e no Nexus, por isso o índice troca sem o lock mudar.
# `PYPI_TRUSTED_HOST` só é preciso quando o índice serve em HTTP.
FROM base AS deps
ARG PYPI_INDEX_URL=
ARG PYPI_TRUSTED_HOST=
RUN python -m venv /opt/venv
COPY requirements.txt ./
COPY wheels/ wheels/
RUN pip install --no-deps --require-hashes \
        ${PYPI_INDEX_URL:+--index-url "$PYPI_INDEX_URL"} \
        ${PYPI_TRUSTED_HOST:+--trusted-host "$PYPI_TRUSTED_HOST"} \
        -r requirements.txt

# ─── Verificação ──────────────────────────────────────────────────────────────
# Só com `--target test`. As ferramentas de desenvolvimento ficam fora da
# imagem de execução.
FROM deps AS test
ARG PYPI_INDEX_URL=
ARG PYPI_TRUSTED_HOST=
COPY requirements-dev.txt ./
RUN pip install --no-deps --require-hashes \
        ${PYPI_INDEX_URL:+--index-url "$PYPI_INDEX_URL"} \
        ${PYPI_TRUSTED_HOST:+--trusted-host "$PYPI_TRUSTED_HOST"} \
        -r requirements-dev.txt
COPY . .
CMD ["sh", "-c", "ruff check . && ruff format --check . && mypy app && pytest -q"]

# ─── Execução ─────────────────────────────────────────────────────────────────
FROM base AS runtime

# Não-root, com uid fixo para as permissões serem previsíveis entre máquinas.
RUN useradd --system --uid 1001 --user-group --no-create-home app

COPY --from=deps /opt/venv /opt/venv
COPY --chown=app:app app/ app/

USER app
EXPOSE 8000

# A imagem não traz curl, e o interpretador chega.
HEALTHCHECK --interval=10s --timeout=3s --retries=5 --start-period=10s \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)"

# Gunicorn a gerir workers uvicorn: o uvicorn sozinho não repõe um worker que
# morra.
# `--no-control-socket`: o socket ia para `$HOME/.gunicorn`, que o `app` não
# pode criar.
CMD ["gunicorn", "app.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--no-control-socket", \
     "--workers", "2", \
     "--bind", "0.0.0.0:8000", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--graceful-timeout", "30", \
     "--timeout", "60"]
