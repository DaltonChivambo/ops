/**
 * Os estados de um caso — nome, cor e a frase do tempo. Consumido pela tabela
 * dos casos, pelo filtro e pelo painel de detalhe: sem um sítio só, cada um
 * dizia «Em análise na SIMO» à sua maneira e com a sua cor.
 */
import type { CaseStatus } from './models';

/** Pela ordem do trabalho: por analisar, connosco, na SIMO, fechado. */
export const CASE_STATUSES: readonly CaseStatus[] = [
  'pending',
  'in-review-internal',
  'in-review-simo',
  'resolved',
];

/** Os que ainda pedem trabalho — a fila. Regularizado é histórico. */
export const OPEN_CASE_STATUSES: readonly CaseStatus[] = CASE_STATUSES.filter(
  (status) => status !== 'resolved',
);

export const CASE_STATUS_LABEL: Record<CaseStatus, string> = {
  pending: 'Pendente',
  'in-review-internal': 'Em análise interna',
  'in-review-simo': 'Em análise na SIMO',
  resolved: 'Regularizado',
};

/** O que se diz do tempo que o caso leva no estado em que está. */
export const CASE_STATUS_WAIT: Record<CaseStatus, string> = {
  pending: 'por analisar há',
  'in-review-internal': 'em análise há',
  'in-review-simo': 'submetido à SIMO há',
  resolved: 'regularizado há',
};

/**
 * Cinzento por analisar, navy connosco, céu do lado da SIMO (fora de casa),
 * verde fechado — cores que não colidem com as do tipo (vermelho/âmbar) nem
 * com as do prazo, que já falam de urgência.
 */
export const CASE_STATUS_DOT: Record<CaseStatus, string> = {
  pending: 'bg-gray-400',
  'in-review-internal': 'bg-moza-500',
  'in-review-simo': 'bg-sky-500',
  resolved: 'bg-emerald-500',
};

export const CASE_STATUS_BADGE: Record<CaseStatus, string> = {
  pending: 'bg-gray-100 text-gray-700',
  'in-review-internal': 'bg-moza-100 text-moza-700',
  'in-review-simo': 'bg-sky-50 text-sky-800',
  resolved: 'bg-emerald-50 text-emerald-800',
};
