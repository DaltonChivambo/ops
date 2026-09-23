#!/usr/bin/env bash
# Verificar, construir e distribuir um pacote interno (ex.: mozaops-libs).
#
#   ci/package.sh check   <pacote>             lock em dia, ruff, mypy e pytest
#   ci/package.sh build   <pacote>             wheel em <pacote>/dist/
#   ci/package.sh vendor  <pacote> <serviço>   o serviço passa a usar a versão actual
#   ci/package.sh publish <pacote>             envia o wheel para PYPI_PUBLISH_URL
#
# Um serviço só muda de versão de um pacote quando alguém corre o `vendor` para
# ele: é isso que deixa cada serviço actualizar ao seu ritmo.
#
# O `publish` é para quando houver um repositório onde publicar. Lê
# PYPI_PUBLISH_URL, e as credenciais em UV_PUBLISH_USERNAME e UV_PUBLISH_PASSWORD.
set -euo pipefail
export MSYS_NO_PATHCONV=1

command=${1:?"uso: $0 <check|build|vendor|publish> <pasta do pacote> [serviço]"}
dir=${2:?"falta a pasta do pacote"}
dir=${dir%/}
here=$(dirname "$0")

name=$(sed -n 's/^name = "\(.*\)"$/\1/p' "$dir/pyproject.toml" | head -1)
version=$(sed -n 's/^version = "\(.*\)"$/\1/p' "$dir/pyproject.toml" | head -1)
wheel="${name//-/_}-$version-py3-none-any.whl"

UV_IMAGE=ghcr.io/astral-sh/uv:0.12.1-python3.14-trixie-slim

uv() {
  local host_dir
  host_dir=$(cd "$dir" && { pwd -W 2>/dev/null || pwd; })
  docker run --rm -e UV_PROJECT_ENVIRONMENT=/tmp/venv \
    -e UV_PUBLISH_USERNAME -e UV_PUBLISH_PASSWORD \
    -v "$host_dir:/src" -w /src "$UV_IMAGE" sh -c "$1"
}

case "$command" in
  check)
    echo "── $name"
    uv "uv lock --check -q && uv run -q ruff check . && uv run -q ruff format --check . \
      && uv run -q mypy src && uv run -q pytest -q"
    ;;
  build)
    uv "rm -rf dist && uv build -q --wheel -o dist"
    ;;
  vendor)
    service=${3:?"falta a pasta do serviço"}
    service=${service%/}
    [[ -f "$dir/dist/$wheel" ]] || "$0" build "$dir"
    rm -f "$service/wheels/${name//-/_}-"*.whl
    mkdir -p "$service/wheels"
    cp "$dir/dist/$wheel" "$service/wheels/"
    sed -i -E \
      -e "s|\"$name==[^\"]+\"|\"$name==$version\"|" \
      -e "s|^($name = \{ path = \"wheels/)[^\"]+|\1$wheel|" \
      "$service/pyproject.toml"
    "$here/service.sh" lock "$service"
    ;;
  publish)
    : "${PYPI_PUBLISH_URL:?falta o PYPI_PUBLISH_URL}"
    "$0" build "$dir"
    uv "uv publish --publish-url '$PYPI_PUBLISH_URL' dist/*"
    ;;
  *)
    echo "comando desconhecido: $command" >&2
    exit 2
    ;;
esac
