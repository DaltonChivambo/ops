# O SPA: compila-se com o Node, serve-se com o nginx.
#
# Duas fases porque o Node e as centenas de MB de node_modules não têm nada que
# fazer em produção. A imagem final leva o `dist/` e mais nada — não há
# compilador, não há gestor de pacotes, não há código-fonte.
#
#   docker build -t mozaops-web frontend

# ─── Compilação ───────────────────────────────────────────────────────────────
FROM node:24-alpine AS build

WORKDIR /app

# O manifesto e o lock primeiro, sozinhos: enquanto as dependências não mudarem,
# esta camada e o `npm ci` que se lhe segue vêm da cache, e mexer no código não
# obriga a reinstalar nada.
#
# `npm ci` e não `npm install`: instala exactamente o que está no lock e falha se
# ele divergir do package.json, em vez de o reescrever a meio de um build.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# `npm run build` é `ng build`, e o angular.json tem `defaultConfiguration:
# production` — o que troca environment.ts por environment.production.ts, onde
# `authDisabled` é `false`. A imagem nunca leva a sessão de desenvolvimento
# dentro, mesmo que quem a construa tenha o ficheiro de dev por commitar.
RUN npm run build

# ─── Execução ─────────────────────────────────────────────────────────────────
FROM nginx:1.31-alpine AS runtime

# O builder do Angular escreve em dist/<projecto>/browser. É essa pasta que se
# serve — a de cima traz ainda prerendered-routes.json e as licenças de
# terceiros, que não são conteúdo do site.
COPY --from=build /app/dist/mozaops-web/browser /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Correr como não-root. O utilizador `nginx` já existe na imagem, mas os
# caminhos onde o processo escreve pertencem ao root — daí o chown. O
# entrypoint da imagem detecta que não é root e salta a auto-configuração, que
# é precisamente o que se quer: a configuração é a que está no ficheiro acima.
RUN chown -R nginx:nginx /var/cache/nginx /var/log/nginx \
    && touch /run/nginx.pid \
    && chown nginx:nginx /run/nginx.pid

USER nginx

# Documental: quem publica portas é o Compose. O Traefik encaminha para aqui,
# e a label do serviço tem de dizer `loadbalancer.server.port=8080`.
EXPOSE 8080

# `wget` vem do busybox do Alpine — a imagem não traz curl, e instalar um só
# para o healthcheck seria pagar uma dependência por três segundos de arranque.
HEALTHCHECK --interval=10s --timeout=3s --retries=5 --start-period=5s \
    CMD wget -q -O /dev/null http://127.0.0.1:8080/ || exit 1
