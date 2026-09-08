/**
 * O catálogo de módulos e funcionalidades — os `id` são segmentos de URL.
 * Só está aqui o que existe (nada de prometer o que ainda não foi construído).
 * Área/ilha espelham `features/<área>/<ilha>/`; `area: null` = transversal.
 */

/**
 * A **área** é a unidade de acesso do MozaOps: quem é dela abre as automações
 * dela, e quem não é nem as vê. Os ids são os mesmos que o backend usa no
 * `AUTH_AREAS` e que o `/api/identity/me` devolve — mudá-los aqui sem os mudar
 * lá tira o acesso a toda a gente.
 *
 * **Não é o departamento.** «Meios de Pagamentos e Canais», o rótulo que a
 * barra lateral mostra, é um Departamento — e dentro dele há várias unidades
 * reais e distintas no organigrama: `CANAIS E SERVIÇOS DE INTEGRAÇÃO`
 * (código GEEA 3230) é uma, `SERVIÇO DE MEIOS DE PAGAMENTO` (2442) é outra.
 * `canais` é a área de quem trata do POS/ATM/Quiosques — a única com
 * automação construída, por isso a única que existe aqui. O rótulo do
 * departamento é só agrupamento visual (`sidebar.ts`); o acesso é à área.
 *
 * O GEEA chama `department` à unidade onde a pessoa está registada, mas o que
 * lá vem tanto é um departamento como uma área ou um serviço.
 */
export type AreaId = 'canais';

export interface Area {
  readonly id: AreaId;
  readonly label: string;
}

/**
 * Só o que já tem automação construída (mesma regra do módulo/funcionalidade).
 * «Clientes e Contas» entra aqui — e ganha `features/customers-and-accounts/`
 * com conteúdo — quando tiver a primeira.
 */
export const AREAS: readonly Area[] = [{ id: 'canais', label: 'Canais' }];

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
  /** null = transversal, não é de nenhuma área (ex: Dashboard). Toda a gente
      com sessão o abre — o que lá está não é de ninguém em particular. */
  readonly area: AreaId | null;
  /** A ilha, dentro do Departamento que a barra lateral mostra — ex: "Canais"
      dentro de "Meios de Pagamentos e Canais". Coincide com a área quando a
      ilha já tem automação construída (é o caso de "Canais" hoje). */
  readonly section: string;
  readonly icon: ModuleIcon;
  readonly features: readonly Feature[];
}

/**
 * A automação é do canal POS e só dele: o serviço expõe
 * `/pos/validacao-credito-fecho`, e o ficheiro de entrada, as regras e o
 * relatório são os do POS.
 */
const CLOSING_VALIDATION: Feature = {
  id: 'closing-credit-validation',
  title: 'Validação de Crédito de Valores de Fecho de POS',
  description:
    'Confirma que os valores de fecho dos POS apurados no Portal SIMO foram ' +
    'efectivamente creditados nas contas à ordem dos comerciantes no Banka, ' +
    'classifica as divergências e gera o relatório do departamento.',
  category: 'Fecho',
  available: true,
};

export const MODULES: readonly NavModule[] = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    area: null,
    section: 'Geral',
    icon: 'layout-grid',
    features: [],
  },
  {
    id: 'pos',
    label: 'POS',
    area: 'canais',
    section: 'Canais',
    icon: 'smartphone-nfc',
    features: [CLOSING_VALIDATION],
  },
  {
    id: 'atm',
    label: 'ATM',
    area: 'canais',
    section: 'Canais',
    icon: 'landmark',
    features: [],
  },
  {
    id: 'kiosks',
    label: 'Quiosques',
    area: 'canais',
    section: 'Canais',
    icon: 'store',
    features: [],
  },
];

export const SECTIONS: readonly string[] = ['Geral', 'Canais'];

export function findModule(id: string): NavModule | undefined {
  return MODULES.find((module) => module.id === id);
}

export function modulesOfSection(section: string): readonly NavModule[] {
  return MODULES.filter((module) => module.section === section);
}

export function areaLabel(id: string): string | undefined {
  return AREAS.find((area) => area.id === id)?.label;
}
