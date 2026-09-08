# 0009 — Autenticação contra o GEEA, sem Keycloak próprio

- **Estado**: Aceite
- **Data**: 2026-09-06
- **Decisor(es)**: Dalton Chivambo

## Contexto

O plano original (ADR 0007) punha um Keycloak nosso à frente da aplicação, federado
contra o Active Directory do banco. Nunca chegou a federar: o bloco de LDAP exige
dados que só a equipa de IAM tem — `connectionUrl`, `bindDn` e a password da conta
de serviço — e esperar por eles deixava a aplicação inteira sem autenticação, com
as rotas abertas e um `authDisabled: true` no frontend.

Entretanto ficou claro que o banco já tem o que faltava. O **GEEA** é o Keycloak
corporativo, já federado com o AD, já a servir outras aplicações internas, e expõe
um `SSOLogin` que troca credenciais do domínio por um token assinado. Pedir à
equipa de IAM um realm novo, dedicado ao MozaOps, seria pedir uma segunda cópia
do directório para manter — e o segundo sítio onde alguém se esquece de desactivar
quem saiu do banco.

## Decisão

**O MozaOps não tem servidor de identidade próprio.** O Keycloak `mozaops`, o realm
exportado em `infra/keycloak/` e os três utilizadores de teste desaparecem.

Em vez disso:

1. Um serviço `platform/identity` é o **único** que fala com o GEEA. Recebe as
   credenciais do SPA num `POST`, chama o `SSOLogin`, e devolve um token de acesso
   no corpo e um token de renovação num cookie `HttpOnly`.
2. Todos os serviços **validam** os tokens do GEEA localmente, contra o JWKS dele,
   com o `mozaops_libs/auth` partilhado. Validar é barato e não precisa de rede a
   cada pedido; emitir é que é privilégio de quem tem o directório.
3. O SPA guarda o token de acesso **em memória** e renova-o pelo cookie. Nada de
   `localStorage`: aí, um XSS vale uma sessão inteira em vez de um pedido.
4. Em desenvolvimento, um mock do GEEA (`external-services/geea-keycloak`) assina
   RS256 com uma chave própria e publica o JWKS. Vive fora de `backend/` de
   propósito — não é um serviço nosso, é a simulação de um serviço de terceiros.

## Consequências

- **Uma password a menos.** As credenciais são as do Windows; não há conta MozaOps
  para criar, repor ou desactivar. Quem sai do banco perde o acesso no mesmo acto.
- **A disponibilidade do GEEA passa a ser nossa.** Se ele estiver em baixo, ninguém
  entra — e quem já entrou trabalha até o token expirar. O `IdentityUnavailableError`
  existe para isso: dizer «o GEEA não respondeu» em vez de «sessão inválida», que
  mandava a pessoa repetir o login para nada.
- **O contrato do `SSOLogin` obriga a password numa query string.** É um requisito
  de quem o expõe, não uma escolha nossa. O que se pode fazer deste lado faz-se: o
  browser manda-a no corpo de um `POST`, e o `configure_logging()` cala o `httpx`
  ao nível INFO para a password não ficar nos logs do container.
- **O ADR 0007 fica sem objecto** — os grupos `DOP-Operadores`, `DOP-Chefias` e
  `Auditoria` nunca chegaram a existir do lado do AD, e o realm que os continha
  desapareceu.

## Alternativas consideradas

**Pedir um realm dedicado ao MozaOps dentro do GEEA.** Mais limpo no papel: papéis
nossos, geridos por nós, sem tocar no realm dos outros. Rejeitado pelo prazo — é um
pedido à equipa de IAM com data de resposta desconhecida, e a alternativa custa-nos
um `map_areas` de trinta linhas.

**Manter o Keycloak nosso e federar mais tarde.** É o que o 0007 previa. Rejeitado:
um ano depois continuava por federar, e entretanto a aplicação corria sem
autenticação nenhuma em nome de uma migração que nunca vinha.

**Reencaminhar para o ecrã de login do GEEA (fluxo `authorization_code`).** É o que
se deve fazer, e é o que a norma manda — o MozaOps deixaria de ver a password de
todo. Não é hoje: obriga a registar o `redirect_uri` do MozaOps no realm QAS, o que
é outra vez um pedido à equipa de IAM. O `SessionService` está desenhado para isso
não doer quando chegar: o que muda é de onde vêm as claims, não o resto.
