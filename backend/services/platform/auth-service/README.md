# auth-service

Quem entra na aplicação, e o que pode fazer lá dentro.

O GEEA — o sistema de identidade do banco — autentica; este serviço traduz o
que ele devolve para o vocabulário do MozaOps e diz ao resto da aplicação com
quem está a falar. Não guarda nada: sem base de dados, sem tabela de
utilizadores, sem sessão em memória.

## Rotas

| | |
|---|---|
| `POST /api/auth-service/sessions` | Login. Credenciais **no corpo**; devolve o token de acesso e põe o de renovação num cookie `HttpOnly` |
| `POST /api/auth-service/sessions/refresh` | Renova a partir do cookie |
| `DELETE /api/auth-service/sessions` | Termina a sessão deste lado |
| `GET /api/auth-service/me` | Quem sou eu, já com as áreas do MozaOps |

## As duas decisões que explicam o resto

**As áreas não vêm do token.** O GEEA traz os papéis do sistema dele
(`work_queue`, `manage_employee`, `manage_organicUnit`) e a unidade orgânica da
pessoa — nada que diga «isto abre a validação de fechos de POS». Quem decide
isso somos nós, em `mozaops_libs.auth.areas`, por configuração. Daí existir o
`/me`: o SPA não consegue chegar a esta conclusão sozinho a partir do token, e
ter a regra no browser significaria publicar o SPA de cada vez que alguém muda
de unidade.

Uma nota de vocabulário: a claim do GEEA chama-se `departmentCode`, mas o que lá
vem é a unidade orgânica — que tanto é um departamento como uma área ou um
serviço. **Área** é a nossa unidade de acesso grossa, e não há papéis dentro
dela: quem a tem faz tudo o que as automações dela fazem.

Ao lado da área há a concessão fina, uma automação de cada vez —
`service:<id>:read` ou `:write` — para quem precisa de uma só, ou de consultar
sem mexer. O `/me` devolve as duas, e o nível vem como `read` ou `write` em
`serviceAccess`. Serve tanto uma pessoa como um programa de outro departamento:
nada aqui os distingue, porque o que muda é só o que lhes foi concedido.

**O token de acesso vai no corpo; o de renovação vai em cookie `HttpOnly`.**
O SPA guarda o de acesso em memória e envia-o no cabeçalho `Authorization`, que
é como os outros serviços o esperam. O de renovação nunca fica ao alcance de
JavaScript, com `Path` limitado a `/api/auth-service` — o que faz com que um XSS na
página não dê a ninguém uma sessão renovável.

## A ressalva do `SSOLogin`

O login é feito pelo `SSOLogin`, uma API legada do GEEA que leva as credenciais
na query string de um `GET`. Isso obriga a aplicação a ver a password **do
domínio** da pessoa, o que é o padrão *password grant* — desaconselhado, e a
evitar assim que a equipa de IAM registar o MozaOps como aplicação no realm
`QAS`. Enquanto for assim:

- O contrato do `SSOLogin` está isolado em `app/infrastructure/geea_client.py`,
  o ficheiro que se apaga no dia da troca.
- O `httpx` regista o URL de cada pedido, e esse URL leva a password. O
  silenciamento está em `settings.configure_logging`, com a razão escrita.
- O 422 de validação não devolve o corpo que falhou, porque esse corpo tem a
  password lá dentro.
- Há limite de tentativas por utilizador, senão a rota é um oráculo de força
  bruta contra contas do domínio.
- O cookie de renovação exige HTTPS fora de desenvolvimento
  (`SESSION_COOKIE_SECURE`).

## Configuração

Ver `app/settings.py` — é a lista completa do que o serviço lê. As variáveis
`AUTH_*` são partilhadas com os outros serviços e vêm do mesmo `${...}` no
`docker-compose.yml`: dois serviços a mapear áreas de maneira diferente seria
uma porta aberta no que ficasse para trás. As excepções são o
`AUTH_SERVICE_AREA` e o `AUTH_SERVICE_ID`, que só as automações declaram — são a
área a que **elas** pertencem e o id por que são concedidas; este serviço não
tem nem uma nem outro.

O `AUTH_CLIENT_ID` diz de que cliente do realm se lêem os papéis. Não é o `azp`
do token: admitir mais um cliente no `AUTH_ALLOWED_AZP` passa a ser admitir um
cliente, e não delegar-lhe a atribuição dos nossos acessos.

## Na rede do banco: onde se mexe

Nada neste serviço tem um endereço escrito. Tudo se mete em `ops/.env` (a partir do
`ops/.env.example`), ou nas variáveis da pipeline.

**Para construir a imagem** (o `Dockerfile` desta pasta):

| Variável | O que é |
|---|---|
| `IMAGE_REGISTRY`, `IMAGE_NAMESPACE` | Harbor: de onde vem a imagem `python:3.14-slim-trixie` |
| `PYPI_INDEX_URL`, `PYPI_TRUSTED_HOST` | Nexus: de onde vêm os pacotes do `requirements.txt` |

**Para correr** (o `app/settings.py`):

| Variável | O que é |
|---|---|
| `GEEA_SSOLOGIN_URL`, `GEEA_TOKEN_URL`, `GEEA_REALM` | onde se faz o login no GEEA |
| `GEEA_CLIENT_ID`, `GEEA_CLIENT_SECRET` | o cliente do MozaOps no GEEA; o segredo vem de quem gere o GEEA |
| `AUTH_ISSUER`, `AUTH_JWKS_URL` | quem emite os tokens e onde estão as chaves; o `AUTH_ISSUER` tem de ser igual ao `iss` dos tokens |
| `AUTH_ALLOWED_AZP`, `AUTH_CLIENT_ID` | que cliente conta; `qa-mozaops` no QAS |
| `AUTH_AREAS`, `AUTH_AREA_USERS` | que unidades e pessoas abrem cada área |
| `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_PATH` | o cookie da sessão |

Este é o único serviço que fala com o GEEA para fazer login, por isso o contentor tem de chegar
ao host do GEEA. Se o nome não resolver dentro do Docker (no log: `SSOLogin inacessível:
ConnectError`), dar-lhe o IP no `ops/.env`: `GEEA_HOSTNAME` e `GEEA_IP` para o GEEA (o login), `KEYCLOAK_HOSTNAME` e
`KEYCLOAK_IP` para o Keycloak (os tokens).

Construir só este serviço, a partir do Harbor e do Nexus, dentro desta pasta:

```bash
docker build \
  --build-arg IMAGE_REGISTRY=<host do Harbor> \
  --build-arg IMAGE_NAMESPACE=<projecto do Harbor> \
  --build-arg PYPI_INDEX_URL=<URL do Nexus, terminado em /simple/> \
  --build-arg PYPI_TRUSTED_HOST=<host do Nexus> \
  -t auth-service:local .
```

Ou, a partir da raiz, `ci/service.sh build backend/services/platform/auth-service`, que lê os
mesmos valores do `ops/.env`.

## Testes

```bash
ci/service.sh check backend/services/platform/auth-service   # a partir da raiz
```

Ou, só com Docker, dentro desta pasta:

```bash
docker build --target test -t auth-service:test . && docker run --rm auth-service:test
```
