# 0007 — Federação LDAP/AD no Keycloak

> Veio do repositório de origem do MozaOps, onde estava numerado 0006. Renumerado ao entrar
> neste monorepo, onde o 0006 já estava tomado.

**Estado:** aceite, por aplicar (bloqueado por dados que não temos)
**Data:** 2026-08-02

## Contexto

O plano coloca a federação com o Active Directory no M0, e não no fim. A razão
não é técnica: se os operadores do DOP tiverem de manter uma password separada
da conta Windows, a adopção sofre e, mais cedo ou mais tarde, alguém partilha
credenciais. Numa aplicação que mexe em contas de comerciantes, isso apaga o
ganho de ter posto autenticação de todo.

## Decisão

O realm `mozaops` federa contra o AD do Moza Banco com:

- **`Edit Mode: READ_ONLY`** — o Keycloak nunca escreve no directório. Passwords,
  nomes e desactivações continuam a ser do AD.
- **`Import Users: on`** — o Keycloak guarda uma cópia local para poder referenciar
  o utilizador em grupos e papéis sem consultar o AD a cada pedido.
- **Papéis locais ao realm**, atribuídos por *mapeamento de grupo*:

  | Grupo no AD | Papel no realm |
  |---|---|
  | `DOP-Operadores` | `operator` |
  | `DOP-Chefias` | `supervisor` |
  | `Auditoria` (Auditoria Interna / Compliance / DRO) | `auditor` |

  Os grupos já existem no realm exportado (`infra/keycloak/realm-mozaops.json`)
  com os papéis associados; falta apenas ligá-los ao AD.

O ponto importante: **a autorização fica do lado do DOP.** Mudar quem é
supervisor passa a ser mover uma pessoa de grupo no AD — não abrir um ticket à
equipa de IAM para mexer no Keycloak.

## Porque é que ainda não está aplicada

O bloco de federação exige dados reais do directório que ninguém fora do banco
tem: o `connectionUrl` (`ldaps://…`), o `bindDn` da conta de serviço e a sua
password, o `usersDn`, e a confirmação de que os grupos acima existem com esses
nomes exactos. Pôr valores inventados no realm seria pior do que não ter nada —
o Keycloak falha no arranque, ou pior, arranca e não federa ninguém sem o dizer.

Em desenvolvimento, os três utilizadores de teste (`operator.test`,
`supervisor.test`, `auditor.test`) cobrem os três papéis e são suficientes.

## Como aplicar, quando os dados existirem

Preferir `kcadm.sh` a mexer na consola — o objectivo é que o realm continue a
ser reconstruível a partir do repositório:

```bash
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh create components \
  -r mozaops \
  -s name=ad-moza \
  -s providerId=ldap \
  -s providerType=org.keycloak.storage.UserStorageProvider \
  -s 'config.vendor=["ad"]' \
  -s 'config.editMode=["READ_ONLY"]' \
  -s 'config.importEnabled=["true"]' \
  -s 'config.connectionUrl=["ldaps://ad.mozabanco.co.mz:636"]' \
  -s 'config.usersDn=["OU=Utilizadores,DC=mozabanco,DC=co,DC=mz"]' \
  -s 'config.bindDn=["CN=svc-keycloak,OU=Servicos,DC=mozabanco,DC=co,DC=mz"]' \
  -s 'config.bindCredential=["<do cofre>"]' \
  -s 'config.usernameLDAPAttribute=["sAMAccountName"]' \
  -s 'config.rdnLDAPAttribute=["cn"]' \
  -s 'config.uuidLDAPAttribute=["objectGUID"]' \
  -s 'config.userObjectClasses=["person, organizationalPerson, user"]'
```

Depois exportar o realm de volta para `infra/keycloak/realm-mozaops.json` — **sem
o `bindCredential`**, que fica no cofre — e commitar.

## Consequências

- Uma queda do AD impede logins novos; quem já tem token continua a trabalhar
  até 15 minutos (`accessTokenLifespan`).
- A revisão de configuração do Keycloak com a equipa de Segurança, prevista para
  antes do M8, passa a ter de cobrir também este bloco: um LDAP mal configurado
  (por exemplo `ldap://` em vez de `ldaps://`) expõe credenciais na rede interna.
