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

Os JWT em `output.accessToken`/`output.refreshToken` são assinados com
`GEEA_KEYCLOAK_JWT_SECRET` (HS256) — é um segredo só deste mock, não
precisa de bater certo com nenhuma chave real. As claims do utilizador
(`name`, `email`, `department`, etc.) vêm de variáveis `GEEA_MOCK_*`, com
valores por omissão em `.env.example`.

### `GET /departamentos`

Requer `Authorization: Bearer <output.accessToken>` de um login válido
(o JWT assinado, não o objeto `accessToken` das claims). Devolve a lista
completa de unidades organizacionais (o conteúdo de
`data/departamentos.json`), sem alterações.

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

- Tokens são JWT stateless (assinados com `GEEA_KEYCLOAK_JWT_SECRET`) —
  não há sessão em memória, sobrevivem a reinícios do serviço enquanto o
  segredo não mudar.
- Os dados de `/departamentos` vêm de `data/departamentos.json`; para
  atualizar a lista basta editar esse ficheiro.
- O perfil de utilizador nas claims (`name`, `email`, `department`,
  `function`, etc.) é fixo por configuração — não varia por `username`
  submetido, exceto `preferred_username`, que ecoa o que foi enviado no
  login.
