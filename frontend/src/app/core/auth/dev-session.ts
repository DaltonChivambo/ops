import type { Principal } from './session.store';

/**
 * Utilizador de mentira para `environment.authDisabled`.
 *
 * Traz `operator` + `supervisor` porque o backend concede os dois a quem é
 * chefia no departamento. Para ver o ecrã do auditor, troque por `['auditor']`;
 * para ver o «sem permissão», por `[]`.
 */
export const DEV_PRINCIPAL: Principal = {
  sub: '00000000-0000-0000-0000-000000000000',
  username: 'dchivambo',
  name: 'Dalton Chivambo',
  email: 'daltonchivambo@gmail.com',
  roles: ['operator', 'supervisor'],
  departmentCode: '2350',
  department: 'Departamento de Apoio Operacional',
  function: 'Director',
};
