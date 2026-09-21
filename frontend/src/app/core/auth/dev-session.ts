import { ALL_AREAS } from '../navigation';
import type { Principal } from './session.store';

/**
 * Utilizador de mentira para `environment.authDisabled`.
 *
 * São as claims que o QAS devolve, e não um perfil inventado: com isto ligado
 * vê-se o mesmo que se vê com o GEEA à frente. A unidade é `2350` e não abre
 * área nenhuma por si — no servidor quem abre é o papel que o realm dá ao
 * cliente `qa-mozaops`, e esta pessoa tem o que abre tudo.
 *
 * Para desenhar o que os outros vêem, troque as áreas: `['channels']` dá a
 * barra lateral de quem só é de Canais, e `[]` dá o ecrã de «sem acesso».
 */
export const DEV_PRINCIPAL: Principal = {
  sub: '6961d9f6-5529-457b-93cb-db82230a00cb',
  username: 'm001926',
  // Já sem o apelido repetido, como o `/me` o devolve: o que vem do GEEA é
  // «Dalton Chivambo Chivambo», e é o backend que o corta.
  name: 'Dalton Chivambo',
  email: 'dalton.chivambo@mozabanco.co.mz',
  areas: [ALL_AREAS],
  departmentCode: '2350',
  department: 'Departamento de Apoio Operacional',
  function: 'Director',
};
