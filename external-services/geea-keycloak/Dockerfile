# Sem argumentos, tudo vem da Internet. Na rede do banco os ARG apontam ao
# Harbor e ao Nexus, como nos serviços do MozaOps. A imagem é a mesma deles,
# para o Harbor só ter de guardar uma.
ARG IMAGE_REGISTRY=docker.io
ARG IMAGE_NAMESPACE=library
ARG PYTHON_IMAGE=python:3.14-slim-trixie

FROM ${IMAGE_REGISTRY}/${IMAGE_NAMESPACE}/${PYTHON_IMAGE}
ARG PYPI_INDEX_URL=
ARG PYPI_TRUSTED_HOST=

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir \
        ${PYPI_INDEX_URL:+--index-url "$PYPI_INDEX_URL"} \
        ${PYPI_TRUSTED_HOST:+--trusted-host "$PYPI_TRUSTED_HOST"} \
        -r requirements.txt

COPY app ./app
COPY data ./data

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
