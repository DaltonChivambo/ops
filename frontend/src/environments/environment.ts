/** Desenvolvimento: `ng serve` em 4200, com proxy de /api para os serviços. */
export const environment = {
  production: false,
  /** Vazio = mesma origem. O proxy trata do resto em dev; em produção o
      Traefik serve o SPA e a API do mesmo host, por isso continua vazio. */
  apiBaseUrl: '',
  /**
   * Salta o login e injecta uma sessão falsa (ver `core/auth/dev-session.ts`).
   *
   * Existe para desenhar ecrãs sem ter nada de pé — e só para isso. Com isto
   * ligado não há token, logo os pedidos a `/api/**` saem sem `Authorization`
   * e o backend recusa-os: serve para ver a interface, não para a exercitar
   * ponta a ponta.
   *
   * Está a `false` porque o fluxo real já funciona localmente. Isso significa
   * que o `npm start` pressupõe o `make up` e o mock do GEEA em cima — ver o
   * README. Ligar a `true` devolve a sessão de mentira.
   */
  authDisabled: false,

  /** Sessões e papéis. Ver `backend/services/platform/identity`. */
  identityApiBase: '/api/identity',

  /**
   * Caminho base da automação de fechos.
   *
   * Os segmentos estão em português por serem o contrato herdado do MozaOps v1,
   * que o `ARCHITECTURE.md` §8 regista como a excepção assumida — tudo o resto
   * do código é em inglês. Mudá-los obriga a mexer no router do serviço e no
   * `PathPrefix` do Traefik ao mesmo tempo.
   *
   * Vazio à esquerda porque o `apiBaseUrl` é a mesma origem: em dev o proxy do
   * `ng serve` reencaminha, em produção é o Traefik. É a mesma topologia dos
   * dois lados, que é o ponto de haver um proxy à frente.
   */
  closingApiBase: '/api/pos/validacao-credito-fecho',
};
