#!/usr/bin/env bash
# Verificar, construir e publicar um serviço. Não pressupõe nenhuma ferramenta
# de CI: qualquer pipeline chama isto e passa o ambiente pelas variáveis.
#
#   ci/service.sh check <pasta>   lock em dia, ruff, mypy e pytest
#   ci/service.sh build <pasta>   imagem de execução
#   ci/service.sh push  <pasta>   build e envio para o DOCKER_REGISTRY
#   ci/service.sh lock  <pasta>   refaz o uv.lock e os requirements
#
# Todas opcionais. Sem elas, tudo vem da Internet:
#   PYTHON_BASE_REGISTRY  PYTHON_BASE_NAMESPACE   origem da imagem base
#   PYPI_INDEX_URL        PYPI_TRUSTED_HOST       índice dos pacotes Python
#   DOCKER_REGISTRY                               destino do push
#   IMAGE_TAG                                     por omissão, a versão do pyproject
#   UV_LOCK_ARGS                                  ex.: "--upgrade-package pyjwt"
set -euo pipefail
export MSYS_NO_PATHCONV=1

command=${1:?"uso: $0 <check|build|push|lock> <pasta do serviço>"}
dir=${2:?"falta a pasta do serviço"}
dir=${dir%/}
name=$(basename "$dir")
version=$(sed -n 's/^version = "\(.*\)"$/\1/p' "$dir/pyproject.toml" | head -1)
image="mozaops/$name:${IMAGE_TAG:-$version}"

UV_IMAGE=ghcr.io/astral-sh/uv:0.12.1-python3.14-trixie-slim
EXPORT_ARGS="--frozen --no-emit-project --no-header -q"

uv() {
  local host_dir
  host_dir=$(cd "$dir" && { pwd -W 2>/dev/null || pwd; })
  docker run --rm -v "$host_dir:/src" -w /src "$UV_IMAGE" sh -c "$1"
}

build_args=()
for var in PYTHON_BASE_REGISTRY PYTHON_BASE_NAMESPACE PYPI_INDEX_URL PYPI_TRUSTED_HOST; do
  if [[ -n "${!var:-}" ]]; then build_args+=(--build-arg "$var=${!var}"); fi
done

case "$command" in
  lock)
    uv "uv lock -q ${UV_LOCK_ARGS:-} \
      && uv export $EXPORT_ARGS --no-dev -o requirements.txt \
      && uv export $EXPORT_ARGS --all-groups -o requirements-dev.txt"
    ;;
  check)
    echo "── $name"
    # Os requirements são o que a imagem instala: se divergirem do lock, a
    # imagem não é a que se testou localmente.
    uv "uv lock --check -q \
      && uv export $EXPORT_ARGS --no-dev | cmp -s - requirements.txt \
      && uv export $EXPORT_ARGS --all-groups | cmp -s - requirements-dev.txt" \
      || { echo "uv.lock ou requirements desactualizados: ci/service.sh lock $dir" >&2; exit 1; }
    docker build -q --target test "${build_args[@]}" -t "$name:test" "$dir" >/dev/null
    docker run --rm "$name:test"
    ;;
  build|push)
    docker build --target runtime "${build_args[@]}" -t "$image" "$dir"
    if [[ "$command" == push ]]; then
      : "${DOCKER_REGISTRY:?falta o DOCKER_REGISTRY}"
      docker tag "$image" "$DOCKER_REGISTRY/$image"
      docker push "$DOCKER_REGISTRY/$image"
    fi
    ;;
  *)
    echo "comando desconhecido: $command" >&2
    exit 2
    ;;
esac
