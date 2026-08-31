/**
 * O catálogo de módulos e funcionalidades — os `id` são segmentos de URL.
 * Só está aqui o que existe (nada de prometer o que ainda não foi construído).
 * Departamento/ilha espelham `features/<departamento>/<ilha>/`; `department: null` = transversal.
 */

export type DepartmentId = 'payments-and-channels';

export interface Department {
  readonly id: DepartmentId;
  readonly label: string;
}

/**
 * Só o que já tem automação construída (mesma regra do módulo/funcionalidade).
 * «Clientes e Contas» entra aqui — e ganha `features/customers-and-accounts/`
 * com conteúdo — quando tiver a primeira.
 */
export const DEPARTMENTS: readonly Department[] = [
  { id: 'payments-and-channels', label: 'Meios de Pagamentos e Canais' },
];

export type FeatureId = 'closing-credit-validation';
export type ModuleId = 'dashboard' | 'pos' | 'atm' | 'kiosks';

export interface Feature {
  readonly id: FeatureId;
  readonly title: string;
  readonly description: string;
  readonly category: string;
  /** false enquanto a funcionalidade não estiver construída para este canal. */
  readonly available: boolean;
}

/** Nome que a sidebar traduz para um componente do Lucide. */
export type ModuleIcon = 'layout-grid' | 'smartphone-nfc' | 'landmark' | 'store';

export interface NavModule {
  readonly id: ModuleId;
  readonly label: string;
  /** null = transversal, não pertence a nenhum departamento (ex: Dashboard). */
  readonly department: DepartmentId | null;
  /** A ilha dentro do departamento — ex: "Canais" dentro de Meios de Pagamentos e Canais. */
  readonly section: string;
  readonly icon: ModuleIcon;
  readonly features: readonly Feature[];
}

/**
 * A mesma automação serve os três canais — muda o ficheiro de entrada, não a
 * regra. Por isso é uma fábrica, e não três definições copiadas.
 */
const closingValidation = (channel: string, available: boolean): Feature => ({
  id: 'closing-credit-validation',
  title: 'Validação de Crédito de Valores de Fecho',
  description:
    `Confirma que os valores de fecho dos ${channel} apurados no Portal SIMO foram ` +
    'efectivamente creditados nas contas à ordem dos comerciantes no Banka, ' +
    'classifica as divergências e gera o relatório do departamento.',
  category: 'Fecho',
  available,
});

export const MODULES: readonly NavModule[] = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    department: null,
    section: 'Geral',
    icon: 'layout-grid',
    features: [],
  },
  {
    id: 'pos',
    label: 'POS',
    department: 'payments-and-channels',
    section: 'Canais',
    icon: 'smartphone-nfc',
    features: [closingValidation('POS', true)],
  },
  {
    id: 'atm',
    label: 'ATM',
    department: 'payments-and-channels',
    section: 'Canais',
    icon: 'landmark',
    features: [closingValidation('ATM', false)],
  },
  {
    id: 'kiosks',
    label: 'Quiosques',
    department: 'payments-and-channels',
    section: 'Canais',
    icon: 'store',
    features: [closingValidation('quiosques', false)],
  },
];

export const SECTIONS: readonly string[] = ['Geral', 'Canais'];

export function findModule(id: string): NavModule | undefined {
  return MODULES.find((module) => module.id === id);
}

export function modulesOfSection(section: string): readonly NavModule[] {
  return MODULES.filter((module) => module.section === section);
}
