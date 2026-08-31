/** Desenvolvimento: `ng serve` em 4200, com proxy de /api para os serviços. */
export const environment = {
  production: false,
  keycloakUrl: 'http://sso.mozaops.localhost',
  keycloakRealm: 'mozaops',
  keycloakClientId: 'mozaops-web',
  /** Vazio = mesma origem. O proxy trata do resto em dev; em produção o
      Traefik serve o SPA e a API do mesmo host, por isso continua vazio. */
  apiBaseUrl: '',
  /**
   * Salta o Keycloak e injecta uma sessão falsa (ver `core/auth/dev-session.ts`).
   *
   * Existe para desenhar ecrãs sem ter o SSO de pé — e só para isso. Com isto
   * ligado não há token, logo os pedidos a `/api/**` saem sem `Authorization` e
   * o backend recusa-os: serve para ver a interface, não para a exercitar
   * ponta a ponta. Voltar a `false` devolve o fluxo real.
   *
   * `environment.production.ts` não tem esta chave por omissão — tem-na a
   * `false`, explicitamente, para que ninguém a herde por distracção.
   */
  authDisabled: true,

  /**
   * Caminho base da automação de fechos.
   *
   * Aponta hoje para o Flask do MozaOps v1, que é o único backend que existe —
   * `backend/services/closing-reconciliation/` ainda é andaime sem código. Os
   * segmentos estão em português porque é o contrato da v1.
   *
   * Quando o serviço v2 arrancar, isto passa a
   * `/api/pos/closing-credit-validation` (docs/implementation-plan.md:183) e os
   * segmentos internos deixam de ser em português. É uma linha, e está isolada
   * aqui exactamente por isso.
   */
  closingApiBase: '/api/pos/validacao-credito-fecho',
};
