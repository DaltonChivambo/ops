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
   * Os segmentos estão em português por serem o contrato herdado do MozaOps v1,
   * que o `ARCHITECTURE.md` §7 regista como a excepção assumida — tudo o resto
   * do código é em inglês. Mudá-los obriga a mexer no router do serviço e no
   * `PathPrefix` do Traefik ao mesmo tempo.
   *
   * Vazio à esquerda porque o `apiBaseUrl` é a mesma origem: em dev o proxy do
   * `ng serve` reencaminha, em produção é o Traefik. É a mesma topologia dos
   * dois lados, que é o ponto de haver um proxy à frente.
   */
  closingApiBase: '/api/pos/validacao-credito-fecho',
};
