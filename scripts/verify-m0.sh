#!/usr/bin/env bash
# Critério de «feito» do M0, executável.
#
# Um marco não se dá por concluído com base em impressão: ou este script passa,
# ou o M0 não está feito.
set -uo pipefail

cd "$(dirname "$0")/.."
[[ -f .env ]] && set -a && source .env && set +a

DOMAIN="${DOMAIN:-mozaops.localhost}"
# As credenciais do mock do GEEA. Em produção não há aqui login nenhum a fazer:
# este script é do ambiente local, e é o único sítio onde uma password de mock
# é aceitável.
GEEA_USER="${GEEA_KEYCLOAK_USERNAME:-geea.integracao}"
GEEA_PASS="${GEEA_KEYCLOAK_PASSWORD:-mude-me-em-producao}"

failures=0
ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
fail() { printf '  \033[31m✗\033[0m %s\n' "$1"; failures=$((failures + 1)); }

echo
echo "M0 — Ambiente e infraestrutura local"
echo

# ─── Ferramentas ────────────────────────────────────────────────────────────
echo "Ferramentas"
# Pelo nvm e não pelo PATH herdado: o .bashrc só selecciona a versão default em
# shells interactivos, por isso o `node` que este processo vê pode ser antigo
# mesmo com o default já actualizado. O que interessa é a versão que um terminal
# novo dá — e essa é a do alias `default`.
if [[ -s "$HOME/.nvm/nvm.sh" ]]; then
  node_version=$(. "$HOME/.nvm/nvm.sh" >/dev/null 2>&1 && nvm use default >/dev/null 2>&1 && node --version 2>/dev/null)
else
  node_version=$(node --version 2>/dev/null)
fi
node_version="${node_version:-ausente}"

case "$node_version" in
  v2[2-9].*|v[3-9][0-9].*) ok "Node $node_version (o Angular 22 exige >= 22.22.3)" ;;
  *) fail "Node $node_version — o Angular 22 exige ^22.22.3 || ^24.15.0 || >=26" ;;
esac

if command -v uv >/dev/null 2>&1; then ok "uv $(uv --version | awk '{print $2}')"
else fail "uv não está no PATH"; fi

if docker ps >/dev/null 2>&1; then ok "Docker acessível sem sudo"
else fail "Docker inacessível — falta 'sudo usermod -aG docker \$USER' e voltar a entrar na sessão"; fi

# ─── Containers ─────────────────────────────────────────────────────────────
echo
echo "Containers"
for service in traefik postgres identity otel-collector jaeger; do
  state=$(docker compose ps --format '{{.State}}' "$service" 2>/dev/null | head -1)
  [[ "$state" == "running" ]] && ok "$service" || fail "$service (estado: ${state:-ausente})"
done

# ─── Bases de dados ─────────────────────────────────────────────────────────
echo
echo "Bases de dados"
databases=$(docker compose exec -T postgres psql -U "${POSTGRES_USER:-postgres}" -tAc \
            'SELECT datname FROM pg_database' 2>/dev/null)
for database in mozaops_closing_reconciliation mozaops_cases; do
  grep -qx "$database" <<<"$databases" && ok "$database" || fail "$database em falta"
done

# O REVOKE não é opcional: é ele que faz «database per service» significar algo.
cross=$(docker compose exec -T postgres psql -U "${POSTGRES_USER:-postgres}" -tAc \
        "SELECT has_database_privilege('${DB_CASES_USER:-cases}', 'mozaops_closing_reconciliation', 'CONNECT')" 2>/dev/null | tr -d '[:space:]')
[[ "$cross" == "f" ]] \
  && ok "o role '${DB_CASES_USER:-cases}' NÃO se liga à base da reconciliação" \
  || fail "isolamento cruzado falhou (has_database_privilege devolveu '${cross:-?}')"

# ─── Identidade ─────────────────────────────────────────────────────────────
# O MozaOps não tem servidor de identidade próprio (ADR 0009): autentica contra
# o GEEA e valida os tokens dele localmente. O que se verifica aqui é a cadeia
# inteira — o mock emite, o `identity` troca credenciais por sessão, e a
# automação recusa quem não traz token.
echo
echo "Identidade"

if config=$(curl -fsS --max-time 10 "http://127.0.0.1:8100/auth/realms/QAS/.well-known/openid-configuration" 2>/dev/null); then
  ok "o mock do GEEA responde à descoberta OIDC"
  grep -q 'jwks_uri' <<<"$config" && ok "expõe o jwks_uri (validação local de token)"                                   || fail "sem jwks_uri na descoberta"
else
  fail "o mock do GEEA não responde — 'docker compose -f external-services/geea-keycloak/docker-compose.yml up -d'"
fi

# Login de ponta a ponta, pela porta pública: browser → Traefik → identity → GEEA.
sessao=$(curl -fsS --max-time 10 -X POST   -H 'Content-Type: application/json'   -d "{\"username\":\"${GEEA_USER}\",\"password\":\"${GEEA_PASS}\"}"   "http://${DOMAIN}/api/identity/sessions" 2>/dev/null)

if grep -q '"accessToken"' <<<"$sessao"; then
  ok "o login devolve sessão (credenciais → GEEA → token)"
  grep -q '"areas"' <<<"$sessao"     && ok "a sessão traz as áreas do MozaOps (ADR 0010)"     || fail "a sessão não traz 'areas' — o mapa AUTH_AREAS não foi lido"
else
  fail "o login em http://${DOMAIN}/api/identity/sessions não devolveu sessão"
fi

# A porta fechada é metade do trabalho; provar que está fechada é a outra.
estado=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10          "http://${DOMAIN}/api/pos/validacao-credito-fecho/execucoes/ultima" 2>/dev/null)
[[ "$estado" == "401" ]]   && ok "a automação recusa quem não traz token (401)"   || fail "a automação respondeu ${estado:-?} sem token — devia ser 401"

# ─── Observabilidade ────────────────────────────────────────────────────────
echo
echo "Observabilidade"
curl -fsS --max-time 10 "http://jaeger.${DOMAIN}/" >/dev/null 2>&1 \
  && ok "Jaeger acessível em http://jaeger.${DOMAIN}" \
  || fail "Jaeger não responde em http://jaeger.${DOMAIN}"

echo
if (( failures == 0 )); then
  printf '\033[32mM0 concluído.\033[0m\n\n'
else
  printf '\033[31m%d verificação(ões) por passar — o M0 não está concluído.\033[0m\n\n' "$failures"
fi
exit $(( failures > 0 ))
