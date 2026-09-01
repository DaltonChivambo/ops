# MozaOps — frontend

## O que é a plataforma

O **MozaOps** é a plataforma de automações operacionais do **Moza Banco**, do
Departamento de Meios de Pagamento e Canais (DOP).

Substitui o fecho manual em Excel — exportar do Portal SIMO, do Banka e do MIS e
cruzar à mão com `VLOOKUP` — por execuções auditáveis e persistidas. Cada
processo do departamento é uma **automação**: um módulo com a sua página, as
suas regras e as suas tabelas. Hoje existe uma construída, a validação de
crédito de valores de fecho de POS.

O monorepo tem duas metades que falam uma com a outra: um backend em FastAPI,
com uma base de dados por serviço, e este frontend. Entre o browser e os
serviços está o Traefik, que faz com que ambos partilhem origem — não há CORS
para configurar em lado nenhum.

## O que é esta pasta

**Esta pasta é o frontend, e só ele**: a aplicação de página única em Angular 22
que o operador abre no browser. O backend está em [`../backend/`](../backend/) e
levanta-se à parte.

Para o resto da plataforma:

- **[`../README.md`](../README.md)** — arrancar tudo, backend incluído
- **[`../ARCHITECTURE.md`](../ARCHITECTURE.md)** — o que o sistema é
- **[`../docs/adr/`](../docs/adr/README.md)** — as decisões que custaram a tomar

Angular 22 em modo *standalone*, com *signals* e sem zone.js. Não há
`NgModule`, e a detecção de alterações é reactiva: o que muda o ecrã é um sinal
mudar, não um evento qualquer disparar uma passagem por tudo.

## Requisitos

Só é preciso Node. Nada de Angular CLI global, nada de Docker, nada de backend.

| | Versão | Porquê |
|---|---|---|
| **Node** | `^22.22.3`, `^24.15.0` ou `>= 26` | é o que o próprio Angular 22 exige; abaixo disso o `npm install` recusa. Recomendado o **24 LTS**: `nvm install 24` |
| **npm** | ≥ 8 | vem com o Node |

Verificar o que se tem:

```bash
node -v      # v24.19.0 é o que usamos
npm -v
```

O Angular CLI **não** precisa de estar instalado globalmente — todos os comandos
abaixo passam pelo `npm run`, que usa o CLI local do projecto. Quem preferir
escrever `ng ...` à mão instala-o com `npm i -g @angular/cli@22`.

## Arrancar

A partir desta pasta (`frontend/`):

```bash
npm install        # primeira vez, ou quando o package-lock.json mudar
npm start          # ng serve, já com o proxy do proxy.conf.json
```

Depois abrir **http://localhost:4200/**. A raiz encaminha para a automação dos
fechos de POS. O servidor recompila e recarrega sozinho a cada alteração aos
ficheiros de `src/`.

Com a porta 4200 ocupada:

```bash
npm start -- --port 4300
```

### Precisa do backend?

**Não, para arrancar.** A casca, a navegação e os ecrãs desenham-se à mesma. O
que fica por funcionar é o que precisa de dados: a página dos fechos abre com um
aviso de que não conseguiu carregar a última execução, e não se pode executar
uma validação nova.

Com o backend de pé (`make up` na raiz do monorepo), o `ng serve` reencaminha:

| Prefixo | Destino | |
|---|---|---|
| `/api/pos/validacao-credito-fecho` | `localhost:8001` | serviço `closing-reconciliation` |

O browser fala só com o `localhost:4200`, tal como em produção fala só com o
Traefik. O `pathRewrite` do proxy faz aqui o que o middleware `stripprefix` faz
lá: `/api` é a fronteira da API, não parte do caminho do serviço.

### O que se vê

| Endereço | Ecrã |
|---|---|
| `/` e `/pos` | encaminham para a automação — um canal com automação pronta abre-a directamente |
| `/pos/closing-credit-validation` | Validação de Crédito de Valores de Fecho de POS |
| `/atm`, `/kiosks`, `/dashboard` | aviso de «ainda não disponível»: existem na navegação, sem automação construída |
| `/sem-permissao` | o que um utilizador sem o papel necessário apanha |

## Autenticação, em desenvolvimento

`src/environments/environment.ts` traz `authDisabled: true`. Com isso o Keycloak
é saltado e a aplicação injecta a sessão falsa de
`src/app/core/auth/dev-session.ts` — um utilizador com os papéis `operator` e
`supervisor`.

Isto existe para desenhar ecrãs sem ter o SSO de pé, e só para isso: **não há
token**, logo os pedidos a `/api/**` saem sem `Authorization` e um backend a
sério recusa-os. Para exercitar o fluxo real, pôr `authDisabled: false` e ter o
Keycloak a correr (`make up` na raiz, em http://sso.mozaops.localhost, com os
utilizadores de teste `operator.test` / `supervisor.test` / `auditor.test`).

Para ver a interface como outro papel, trocar os `roles` em `dev-session.ts` —
por exemplo `['auditor']`.

## Como está organizado

```
src/app/
├── core/          navegação, sessão, guardas de rota
├── layout/        a casca: barra lateral, painel do canal, menu do utilizador
├── shared/ui/     as peças que as automações reutilizam
└── features/<departamento>/<ilha>/<automação>/
```

As páginas seguem a organização do departamento — departamento, ilha, automação
— que é a mesma que a barra lateral mostra. Ver o
[README do departamento](src/app/features/payments-and-channels/README.md).

### Peças reutilizáveis

Uma automação nova não recomeça do zero. Em `shared/ui/`:

| | O que traz feito |
|---|---|
| `app-data-table` | cartão, barra de filtros colada, caixa com scroll, scroll infinito, «fim da lista», voltar ao topo. As **colunas são de quem usa** — projectam-se, e por isso cabem tabelas de qualquer formato, incluindo linhas que agrupam e expandem |
| `app-donut-chart` | anel de proporções com legenda e destaque; recebe fatias |
| `app-stacked-bar` | barra empilhada com destaque partilhado com a tabela ao lado |
| `app-stat-card` | indicador, com o corpo do número a descer conforme ele cresce |
| `app-collapsible-card` | cartão que encolhe para o cabeçalho, e lembra-se |
| `<section appCard>` | o cartão branco de que tudo é feito — selector de atributo, para não perder a semântica de `section` |
| `app-toast` | o aviso flutuante |

## Outros comandos

```bash
npm run build      # compila para dist/ (configuração de produção por omissão)
npm run watch      # build de desenvolvimento, em modo contínuo
npm test           # testes unitários
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

Duas fases: o `node:24-alpine` compila, o `nginx:1.31-alpine` serve o `dist/`. A
imagem final tem ~63 MB e não leva Node, nem `node_modules`, nem código-fonte.
Corre como utilizador `nginx`, não como root — daí escutar na **8080** e não na
80, o que a label do Traefik tem de reflectir
(`loadbalancer.server.port=8080`).

A configuração está em [`nginx.conf`](nginx.conf) e faz três coisas que
importam: `try_files` para o `index.html`, senão um F5 em `/pos/...` dá 404;
`no-store` no `index.html` e `immutable` nos ficheiros com hash; e 404 explícito
em `/api/**`, que nunca devia lá chegar — quem encaminha a API é o Traefik.

Como o build usa a configuração de produção, a imagem nunca leva
`authDisabled: true` dentro, mesmo que o ficheiro de dev esteja por commitar.
