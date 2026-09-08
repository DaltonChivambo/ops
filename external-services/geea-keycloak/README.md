# GEEA_KEYCLOAK

Mock standalone de um serviço externo (GEEA) que autentica e devolve a
lista de unidades organizacionais do banco. Não é parte da aplicação
MozaOps — existe fora de `backend/` porque simula um sistema de terceiros
que a aplicação vai consumir, não um serviço nosso.

O login segue o mesmo contrato do `SSOLogin` real (GET com credenciais na
query string, corpo de resposta com `accessToken`/`idToken`/`output`),
para o resto da aplicação poder ser testado contra este mock sem mudar
nada quando trocar para o serviço real.

## Como correr

```bash
cd external-services/geea-keycloak
cp .env.example .env   # opcional — ajusta credenciais/perfil se quiseres
docker compose up -d --build
```

Fica disponível em `http://localhost:8100`.

O container junta-se à rede `mozaops`, criada pelo `docker-compose.yml`
principal — é assim que o backend lhe chega em `http://geea-keycloak:8000`
para ir buscar o JWKS. Por isso, **sobe-se depois do `make up`**; sem a rede
criada, o compose recusa arrancar.

Sem Docker, basta:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8100
```

## Endpoints

### `GET /geea/idmUtils/SSOLogin`

Query params: `realm`, `username`, `password`, `clientId`, `clientSecret`,
`clientIpAdress` (opcional).

```
GET /geea/idmUtils/SSOLogin?realm=QAS&username=geea.integracao&password=mude-me-em-producao&clientId=qa-workflow-ui&clientSecret=mude-me-em-producao&clientIpAdress=127.0.0.1
```

Resposta (forma real replicada — `accessToken`/`idToken` com as claims
decodificadas, `output` com os JWT já assinados a usar como Bearer):

```json
{
  "createdOn": null,
  "modifiedOn": null,
  "modifiedBy": null,
  "createdBy": null,
  "accessToken": { "jti": "...", "exp": 0, "nbf": 0, "iat": 0, "...": "..." },
  "idToken": { "...": "mesma forma do accessToken" },
  "output": {
    "accessToken": "eyJhbGciOi...",
    "expiresIn": "18000",
    "refreshExpiresIn": "18000",
    "refreshToken": "eyJhbGciOi...",
    "tokenType": "bearer",
    "error": null,
    "errorDescription": null
  },
  "clientIpAdress": "127.0.0.1"
}
```

Os JWT em `output.accessToken`/`output.refreshToken` são assinados em
**RS256**, como o GEEA real, com um par RSA gerado ao arranque. Quem valida
vai buscar a chave pública ao JWKS — não há segredo partilhado. As claims do
utilizador (`name`, `email`, `department`, etc.) vêm de variáveis
`GEEA_MOCK_*`, com valores por omissão em `.env.example`.

### `GET /departamentos`

Requer `Authorization: Bearer <output.accessToken>` de um login válido
(o JWT assinado, não o objeto `accessToken` das claims). Devolve a lista
completa de unidades organizacionais (o conteúdo de
`data/departamentos.json`), sem alterações.

### `GET /auth/realms/{realm}/protocol/openid-connect/certs`

O JWKS — as chaves públicas, no mesmo caminho em que um Keycloak as publica.
É por aqui que o backend do MozaOps valida assinaturas.

### `GET /auth/realms/{realm}/.well-known/openid-configuration`

Documento de descoberta, reduzido ao que interessa a quem valida
(`issuer`, `jwks_uri`, algoritmos).

### `GET /health`

Sem autenticação — só para healthcheck.

## Exemplo completo

```bash
TOKEN=$(curl -s "http://localhost:8100/geea/idmUtils/SSOLogin?realm=QAS&username=geea.integracao&password=mude-me-em-producao&clientId=qa-workflow-ui&clientSecret=mude-me-em-producao&clientIpAdress=127.0.0.1" \
  | jq -r .output.accessToken)

curl -s http://localhost:8100/departamentos \
  -H "Authorization: Bearer $TOKEN" | jq
```

## Postman

Importa `postman_collection.json` (Import → arrasta o ficheiro). Tem 3
pedidos — `SSOLogin`, `Get Departamentos`, `Health` — já ligados: o
`SSOLogin` guarda `output.accessToken` numa variável da coleção
(`geea_token`) e o `Get Departamentos` usa-o automaticamente como Bearer
Token.

## Notas

- Tokens são JWT stateless, sem sessão em memória. **O par de chaves é
  gerado a cada arranque**, por isso reiniciar o mock invalida os tokens
  emitidos antes — e é de propósito: obriga quem valida a refrescar o JWKS
  quando aparece um `kid` que não conhece, em vez de assumir que a chave que
  leu uma vez serve para sempre.
- Os dados de `/departamentos` vêm de `data/departamentos.json`; para
  atualizar a lista basta editar esse ficheiro.
- O perfil de utilizador nas claims (`name`, `email`, `department`,
  `function`, etc.) é fixo por configuração — não varia por `username`
  submetido, exceto `preferred_username`, que ecoa o que foi enviado no
  login.
