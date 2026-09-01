import type { Principal } from './session.store';

/**
 * Utilizador de mentira para `environment.authDisabled`. Traz `operator` + `supervisor`
 * porque no realm um é composto sobre o outro. Para o ecrã do auditor, troque por `['auditor']`.
 */
export const DEV_PRINCIPAL: Principal = {
  sub: '00000000-0000-0000-0000-000000000000',
  username: 'dchivambo',
  name: 'Dalton Chivambo',
  email: 'daltonchivambo@gmail.com',
  roles: ['operator', 'supervisor'],
};
