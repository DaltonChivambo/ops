/** Produção: o SPA e a API partilham origem atrás do Traefik, logo não há CORS. */
export const environment = {
  production: true,
  keycloakUrl: 'http://sso.mozaops.localhost',
  keycloakRealm: 'mozaops',
  keycloakClientId: 'mozaops-web',
  apiBaseUrl: '',
  /** Nunca. Está aqui escrito para que a ausência não passe por descuido. */
  authDisabled: false,

  /**
   * O mesmo caminho que em desenvolvimento, e tem de ser: é o que o router do
   * serviço monta (`/pos/validacao-credito-fecho`) e o que o `PathPrefix` do
   * Traefik encaminha, com o `/api` cortado pelo `stripprefix`.
   *
   * Esteve `/api/pos/closing-credit-validation` — um caminho que o backend
   * nunca serviu, herdado de uma renomeação de rotas que não chegou a
   * acontecer. Em produção dava 404 no Traefik.
   */
  closingApiBase: '/api/pos/validacao-credito-fecho',
};
