/**
 * As opções do filtro da coluna «Estado». Consumido por três componentes (tabela,
 * filtro, painel de detalhe) — daí ficar num ficheiro à parte.
 */
import type { DetailCounts, Validation } from './models';

export type StateId = Validation;

export const STATE_OPTIONS: Array<{
  id: StateId;
  label: string;
  validations: Validation[];
  dot: string;
  count: (c: DetailCounts) => number;
}> = [
  {
    id: 'match',
    label: 'Confere',
    validations: ['match'],
    dot: 'bg-emerald-500',
    count: (c) => c.match,
  },
  {
    id: 'mismatch',
    label: 'Incorrecto',
    validations: ['mismatch'],
    dot: 'bg-alert-500',
    count: (c) => c.mismatch,
  },
  {
    id: 'missing',
    label: 'Não creditado',
    validations: ['missing'],
    dot: 'bg-moza-500',
    count: (c) => c.missing,
  },
  {
    id: 'duplicated',
    label: 'Duplicados',
    validations: ['duplicated'],
    dot: 'bg-amber-500',
    count: (c) => c.duplicated,
  },
  // Zerados por último, e em cinzento: é o estado que não pede nada a ninguém.
  {
    id: 'zero',
    label: 'Zerados',
    validations: ['zero'],
    dot: 'bg-gray-300',
    count: (c) => c.zero,
  },
];

export const ALL_STATES = STATE_OPTIONS.map((item) => item.id);

/** Nomes por extenso (tabela/painel), ao contrário dos rótulos curtos do filtro. */
export const STATE_LABEL: Record<Validation, string> = {
  match: 'Confere',
  mismatch: 'Incorrecto',
  missing: 'Não creditado',
  zero: 'Fecho zerado',
  duplicated: 'Períodos duplicados',
};

/** Cor por família: verde confere, quente (vermelho/âmbar) exige trabalho, navy não creditado, cinza zerado. */
export const STATE_DOT: Record<Validation, string> = {
  match: 'bg-emerald-500',
  mismatch: 'bg-alert-500',
  missing: 'bg-moza-500',
  zero: 'bg-gray-300',
  duplicated: 'bg-amber-500',
};

export const STATE_CHIP: Record<Validation, string> = {
  match: 'bg-emerald-50 text-emerald-700',
  mismatch: 'bg-alert-50 text-alert-700',
  missing: 'bg-moza-100 text-moza-600',
  zero: 'bg-gray-100 text-gray-400',
  duplicated: 'bg-amber-50 text-amber-700',
};

/** Régua à esquerda da linha, em todas — sem marca lê-se como "por classificar", não como "em ordem". */
export const STATE_STRIPE: Record<Validation, string> = {
  match: 'border-l-emerald-500',
  mismatch: 'border-l-alert-500',
  missing: 'border-l-moza-400',
  zero: 'border-l-gray-300',
  duplicated: 'border-l-amber-500',
};

/** `null` = todos (sem filtro na query); lista vazia = nenhum. */
export function toValidations(selected: StateId[]): Validation[] | null {
  if (selected.length === ALL_STATES.length) return null;
  return STATE_OPTIONS.filter((item) => selected.includes(item.id)).flatMap(
    (item) => item.validations,
  );
}
