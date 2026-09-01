/**
 * Os papéis do realm `mozaops`. Espelham `infra/keycloak/realm-mozaops.json`.
 *
 * `supervisor` é composto sobre `operator` no Keycloak — quem é supervisor traz
 * os dois papéis no token, por isso aqui não é preciso hierarquia nenhuma.
 */
export const ROLES = ['operator', 'supervisor', 'auditor'] as const;

export type Role = (typeof ROLES)[number];

/** Quem pode correr automações e editar casos. */
export const WRITERS: readonly Role[] = ['operator', 'supervisor'];

/** Quem pode ver — toda a gente com acesso à plataforma. */
export const READERS: readonly Role[] = ['operator', 'supervisor', 'auditor'];

/**
 * Marcar um caso como regularizado declara «este dinheiro está apurado» e a data
 * vai para o relatório do departamento. É o único acto do sistema com significado
 * financeiro, e por isso não é do operador.
 */
export const RESOLVERS: readonly Role[] = ['supervisor'];

export const ROLE_LABELS: Record<Role, string> = {
  operator: 'Operador',
  supervisor: 'Supervisor',
  auditor: 'Auditor',
};
