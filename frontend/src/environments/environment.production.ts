/** Produção: o SPA e a API partilham origem atrás do Traefik, logo não há CORS. */
export const environment = {
  production: true,
  keycloakUrl: 'http://sso.mozaops.localhost',
  keycloakRealm: 'mozaops',
  keycloakClientId: 'mozaops-web',
  apiBaseUrl: '',
  /** Nunca. Está aqui escrito para que a ausência não passe por descuido. */
  authDisabled: false,

  /** O contrato v2 — o Traefik encaminha para `closing-reconciliation`. */
  closingApiBase: '/api/pos/closing-credit-validation',
};
