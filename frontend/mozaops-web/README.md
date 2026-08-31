# MozaOps — frontend

O SPA em Angular 22 (standalone, signals, zoneless) que serve as automações do
departamento. Faz parte do monorepo: ver o `README.md` da raiz para o resto da
plataforma, e `plan.md` para as convenções.

## Pré-requisitos

| | Versão | Notas |
|---|---|---|
| Node | **≥ 22.22.3** (usamos 24 LTS) | O Angular 22 não instala com menos. `nvm install 24` |
| npm | 11.x | vem com o Node 24 |

O Angular CLI não precisa de estar instalado globalmente — todos os comandos
abaixo passam pelo `npm run`, que usa o CLI local do projecto. Se preferir
escrever `ng ...` à mão, `npm i -g @angular/cli@22`.

## Arrancar

A partir desta pasta (`frontend/mozaops-web/`):

```bash
npm install
npm start          # ng serve, com o proxy de proxy.conf.json
```

Depois abrir **http://localhost:4200/** — a raiz redirecciona para `/pos`. O
servidor recarrega sozinho a cada alteração aos ficheiros de `src/`.

Se a porta 4200 estiver ocupada:

```bash
npm start -- --port 4300
```

### O que se vê

| Rota | Ecrã |
|---|---|
| `/pos` | catálogo das automações do canal POS |
| `/pos/closing-credit-validation` | a automação de validação de crédito de fecho |
| `/atm`, `/kiosks`, `/dashboard` | os restantes canais da barra lateral |
| `/sem-permissao` | o que um utilizador sem o papel necessário apanha |

## Autenticação, em desenvolvimento

`src/environments/environment.ts` traz `authDisabled: true`. Com isso o
Keycloak é saltado e a aplicação injecta a sessão falsa de
`src/app/core/auth/dev-session.ts` — um utilizador com os papéis `operator` e
`supervisor`.

Isto existe para desenhar ecrãs sem ter o SSO de pé, e só para isso: **não há
token**, logo os pedidos a `/api/**` saem sem `Authorization` e um backend a
sério recusa-os. Para exercitar o fluxo real, pôr `authDisabled: false` e ter o
Keycloak a correr (`make up` na raiz, em http://sso.mozaops.localhost, com os
utilizadores de teste `operator.test` / `supervisor.test` / `auditor.test`).

Para ver a interface como outro papel, trocar os `roles` em `dev-session.ts` —
por exemplo `['auditor']`.

## Backends

O browser fala só com o `localhost:4200`, tal como em produção fala só com o
Traefik: não há CORS em lado nenhum, e a topologia de dev é a mesma que corre em
produção. O `ng serve` reencaminha, segundo `proxy.conf.json`:

| Prefixo | Destino | |
|---|---|---|
| `/api/pos/validacao-credito-fecho` | `localhost:5000` | Flask do MozaOps v1 — **temporário** |
| `/api/cases` | `localhost:8002` | serviço `cases` |
| `/api` | `localhost:8001` | serviço `closing-reconciliation` |

Nenhum deles precisa de estar de pé para o frontend arrancar: a casca, a
navegação e os ecrãs desenham-se à mesma, e os pedidos falham em silêncio no
painel de rede. Sem o Flask v1 na 5000, o ecrã da automação de fechos aparece
mas sem dados.

## Outros comandos

```bash
npm run build      # compila para dist/ (configuração de produção por omissão)
npm run watch      # build de desenvolvimento, em modo contínuo
npm test           # testes unitários com Vitest
npx prettier --write src   # formatação
```

O `build` de produção substitui `environment.ts` por
`environment.production.ts`, onde `authDisabled` é `false` explicitamente — para
que ninguém herde a sessão falsa por distracção.

## Imagem Docker

```bash
docker build -t mozaops-web .
docker run --rm -p 8099:8080 mozaops-web   # http://localhost:8099
```

Duas fases: o `node:24-alpine` compila, o `nginx:1.31-alpine` serve o `dist/`.
A imagem final tem ~63 MB e não leva Node, nem `node_modules`, nem
código-fonte. Corre como utilizador `nginx`, não como root — daí escutar na
**8080** e não na 80, o que a label do Traefik tem de reflectir
(`loadbalancer.server.port=8080`).

A configuração está em [`nginx.conf`](nginx.conf) e faz três coisas que
importam: `try_files` para o `index.html`, senão um F5 em `/pos/...` dá 404;
`no-store` no `index.html` e `immutable` nos ficheiros com hash; e 404 explícito
em `/api/**`, que nunca devia lá chegar — quem encaminha a API é o Traefik.

Como o build usa a configuração de produção, a imagem nunca leva
`authDisabled: true` dentro, mesmo que o ficheiro de dev esteja por commitar.
