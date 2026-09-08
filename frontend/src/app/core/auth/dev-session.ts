import type { Principal } from './session.store';

/**
 * Utilizador de mentira para `environment.authDisabled`.
 *
 * Traz a área da única automação que existe, porque é o que deixa ver os
 * ecrãs. Para ver o «sem acesso», troque as áreas por `[]`.
 */
export const DEV_PRINCIPAL: Principal = {
  sub: '00000000-0000-0000-0000-000000000000',
  username: 'dchivambo',
  name: 'Dalton Chivambo',
  email: 'daltonchivambo@gmail.com',
  areas: ['payments-and-channels'],
  departmentCode: '2350',
  department: 'Departamento de Apoio Operacional',
  function: 'Director',
};
