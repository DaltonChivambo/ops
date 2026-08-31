# syntax=docker/dockerfile:1
# CONTEXTO DE BUILD: raiz do monorepo (ADR 0005).
#   docker build -f backend/services/ticketing/Dockerfile .

FROM python:3.12-slim AS build
ENV PIP_NO_CACHE_DIR=1 PYTHONDONTWRITEBYTECODE=1
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# A lib partilhada primeiro: muda menos que o serviço, fica em camada cacheada.
COPY backend/libs/ops_common /app/libs/ops_common
RUN pip install /app/libs/ops_common

COPY backend/services/ticketing/pyproject.toml /app/
COPY backend/services/ticketing/src /app/src
RUN pip install /app

FROM python:3.12-slim AS runtime
ENV PYTHONUNBUFFERED=1 PATH="/opt/venv/bin:$PATH" PYTHONPATH=/app/src
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd --system ops && useradd --system --gid ops --home /app ops
WORKDIR /app
COPY --from=build /opt/venv /opt/venv
COPY backend/services/ticketing/src /app/src
COPY backend/services/ticketing/alembic /app/alembic
COPY backend/services/ticketing/alembic.ini /app/alembic.ini
USER ops
EXPOSE 8002
CMD ["uvicorn", "ticketing.main:app", "--host", "0.0.0.0", "--port", "8002"]
