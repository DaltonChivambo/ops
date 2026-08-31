# Realm do MozaOps

`realm-mozaops.json` é importado no arranque (`start-dev --import-realm`). O
realm é **infraestrutura como código**: alterar aqui e recriar o container, nunca
só na consola de administração — uma alteração feita na consola perde-se no
próximo `make clean`.

> **O JSON não aceita comentários nem campos fora do esquema.** O
> `RealmRepresentation` do Keycloak rejeita qualquer chave que não conheça e o
> import falha inteiro (`Unrecognized field`). É por isso que o racional está
> aqui e não lá dentro. Os campos `description` de papéis e clientes são
> legítimos e vão para a consola — esses ficam no JSON.

## Sessões e tokens

`accessTokenLifespan` de 15 minutos, `ssoSessionIdleTimeout` de 30. O token curto
serve dois lados: uma queda do Keycloak não interrompe quem já está a trabalhar
(os serviços validam localmente pelo JWKS em cache), e um token comprometido não
fica válido muito tempo. Os 30 minutos de inactividade batem certo com o
`sessionTimeout` do `withAutoRefreshToken` no frontend.

## Papéis

`supervisor` é **composto** sobre `operator` — herda tudo e acrescenta marcar um
caso como regularizado, reabrir casos e apagar execuções.

A separação existe por uma razão só: marcar `regularizado` é o único acto do
sistema com significado financeiro. Declara «este dinheiro está apurado» e a data
vai para o relatório do departamento. Num banco, quem declara não deve ser sempre
quem executa.

`auditor` não é opcional. Sem um papel só-de-leitura, dar acesso à Auditoria
significa dar-lhe `operator` — e um auditor com botão de upload é um problema de
controlo interno.

Não há `administrador`: as roles `realm-management` do próprio Keycloak cobrem a
gestão de utilizadores, e não há configuração aplicacional para gerir.

## Clientes

| Cliente | Porquê assim |
|---|---|
| `mozaops-web` | Público com PKCE S256. Uma SPA não consegue guardar um segredo, por isso não tem nenhum. Implicit e direct grants desligados. Leva *audience mappers* para os dois serviços, para que um só token sirva ambos |
| `closing-reconciliation` | Confidencial. Servidor de recursos **e** conta de serviço — é ele que publica os casos, com o papel `cases:write-batch` |
| `casos` | Confidencial. Não chama ninguém, por isso não tem conta de serviço |

Sobre a audiência partilhada: um token válido nos dois serviços significa que um
serviço comprometido pode reencaminhá-lo para o outro. Para dois serviços
internos atrás da firewall do banco, aceita-se; *token exchange* (RFC 8693) seria
over-engineering. Ver o ADR 0004 — tem o gatilho de revisão.

## Segredos

**Os segredos no ficheiro são de desenvolvimento** e estão nomeados para que não
haja dúvida (`dev-only-…-change-in-production`). Em produção:

```bash
openssl rand -hex 32                    # gerar
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh update \
  clients/<id> -r mozaops -s secret=<novo>
```

e guardar no cofre. O segredo de produção nunca entra no repositório.

## Grupos e federação

Os grupos `DOP-Operadores`, `DOP-Chefias` e `Auditoria` existem já com os papéis
ligados, mas ainda não estão presos ao Active Directory — falta o `bindDn` e o
`usersDn` reais do banco. Ver `docs/adr/0006-ldap-federation.md`.

## Utilizadores de teste

`operator.test`, `supervisor.test`, `auditor.test` — password igual ao nome do
papel. Só existem para desenvolvimento; em produção as pessoas vêm do AD.

## Exportar depois de mexer na consola

```bash
docker compose exec keycloak /opt/keycloak/bin/kc.sh export \
  --dir /tmp/export --realm mozaops --users realm_file
docker compose cp keycloak:/tmp/export/mozaops-realm.json infra/keycloak/realm-mozaops.json
```

Rever o resultado antes de commitar: o export traz `id`s gerados e segredos, e
nenhum dos dois deve entrar no repositório sem passar pelos olhos.
