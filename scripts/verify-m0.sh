#!/usr/bin/env bash
# Critério de «feito» do M0, executável.
#
# Um marco não se dá por concluído com base em impressão: ou este script passa,
# ou o M0 não está feito.
set -uo pipefail

cd "$(dirname "$0")/.."
[[ -f .env ]] && set -a && source .env && set +a

DOMAIN="${DOMAIN:-mozaops.localhost}"
SSO_DOMAIN="${SSO_DOMAIN:-sso.mozaops.localhost}"
REALM="${KEYCLOAK_REALM:-mozaops}"

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
for service in traefik postgres keycloak otel-collector jaeger; do
  state=$(docker compose ps --format '{{.State}}' "$service" 2>/dev/null | head -1)
  [[ "$state" == "running" ]] && ok "$service" || fail "$service (estado: ${state:-ausente})"
done

# ─── Bases de dados ─────────────────────────────────────────────────────────
echo
echo "Bases de dados"
databases=$(docker compose exec -T postgres psql -U "${POSTGRES_USER:-postgres}" -tAc \
            'SELECT datname FROM pg_database' 2>/dev/null)
for database in mozaops_closing_reconciliation mozaops_cases keycloak; do
  grep -qx "$database" <<<"$databases" && ok "$database" || fail "$database em falta"
done

# O REVOKE não é opcional: é ele que faz «database per service» significar algo.
cross=$(docker compose exec -T postgres psql -U "${POSTGRES_USER:-postgres}" -tAc \
        "SELECT has_database_privilege('${DB_CASES_USER:-cases}', 'mozaops_closing_reconciliation', 'CONNECT')" 2>/dev/null | tr -d '[:space:]')
[[ "$cross" == "f" ]] \
  && ok "o role '${DB_CASES_USER:-cases}' NÃO se liga à base da reconciliação" \
  || fail "isolamento cruzado falhou (has_database_privilege devolveu '${cross:-?}')"

# ─── Keycloak ───────────────────────────────────────────────────────────────
echo
echo "Keycloak"
discovery="http://${SSO_DOMAIN}/realms/${REALM}/.well-known/openid-configuration"
if config=$(curl -fsS --max-time 10 "$discovery" 2>/dev/null); then
  ok "descoberta OIDC responde no realm '${REALM}'"
  grep -q 'jwks_uri' <<<"$config" && ok "expõe o jwks_uri (validação local de token)" \
                                  || fail "sem jwks_uri na descoberta"
else
  fail "descoberta OIDC não responde em ${discovery}"
fi

# Login real de ponta a ponta. O direct grant está desligado no mozaops-web (e
# bem), por isso usa-se a conta de serviço para provar que o realm emite tokens.
token=$(curl -fsS --max-time 10 \
  -d 'grant_type=client_credentials' \
  -d 'client_id=closing-reconciliation' \
  -d "client_secret=${CLIENT_RECONCILIATION_SECRET:-dev-only-closing-reconciliation-change-in-production}" \
  "http://${SSO_DOMAIN}/realms/${REALM}/protocol/openid-connect/token" 2>/dev/null \
  | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

if [[ -n "$token" ]]; then
  ok "a conta de serviço obtém token (client credentials)"
  payload=$(cut -d. -f2 <<<"$token" | tr '_-' '/+')
  payload=$(printf '%s' "$payload$(printf '=%.0s' $(seq $(( (4 - ${#payload} % 4) % 4 ))))" | base64 -d 2>/dev/null)
  grep -q 'write-batch' <<<"$payload" \
    && ok "o token traz o papel 'cases:write-batch'" \
    || fail "o token não traz 'write-batch' — a conta de serviço não ficou com o papel"
else
  fail "não foi possível obter token de conta de serviço"
fi

for username in operator.test supervisor.test auditor.test; do
  exists=$(docker compose exec -T postgres psql -U "${DB_KEYCLOAK_USER:-keycloak}" -d keycloak -tAc \
           "SELECT 1 FROM user_entity WHERE username = '${username}'" 2>/dev/null | tr -d '[:space:]')
  [[ "$exists" == "1" ]] && ok "utilizador ${username}" || fail "utilizador ${username} em falta"
done

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
