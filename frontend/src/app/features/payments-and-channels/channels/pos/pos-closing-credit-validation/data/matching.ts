import type { ClosingMatch } from './models';

/**
 * Pares fecho ↔ crédito, do lado do ecrã. A regra do par (valor igual, cada
 * lado uma vez) é do servidor — `domain/matching.py` — e chega já aplicada nos
 * `suggestedMatches`. Aqui só se trabalha o rascunho e se lê o que veio.
 */

/** closingId → movementId: a forma de trabalho do rascunho — um par por fecho, sem procurar. */
export type MatchDraft = Readonly<Record<string, string>>;

export const toDraft = (matches: readonly ClosingMatch[]): MatchDraft =>
  Object.fromEntries(matches.map((match) => [match.closingId, match.movementId]));

export const toMatches = (draft: MatchDraft): ClosingMatch[] =>
  Object.entries(draft).map(([closingId, movementId]) => ({ closingId, movementId }));

export const sameDraft = (a: MatchDraft, b: MatchDraft): boolean => {
  const keys = Object.keys(a);
  return keys.length === Object.keys(b).length && keys.every((key) => a[key] === b[key]);
};

/**
 * Valor igual ao cêntimo. O JSON traz os montantes como número de vírgula
 * flutuante; comparar os cêntimos inteiros é o que o `Decimal` do servidor faz.
 */
export const sameAmount = (a: number, b: number): boolean =>
  Math.round(a * 100) === Math.round(b * 100);

/**
 * "3 dias depois" / "no mesmo dia" — o sentido vai no valor, não no cabeçalho.
 * `null` numa chave com vários fechos: não se sabe qual crédito é de qual.
 */
export function creditedWhen(
  closingIso: string | undefined,
  creditIso: string | null,
): string | null {
  if (!closingIso || !creditIso) return null;
  const day = 24 * 60 * 60 * 1000;
  const closing = new Date(`${closingIso.slice(0, 10)}T00:00:00`).getTime();
  const credit = new Date(`${creditIso.slice(0, 10)}T00:00:00`).getTime();
  const days = Math.round((credit - closing) / day);
  if (days === 0) return 'no mesmo dia';
  const span = `${Math.abs(days)} ${Math.abs(days) === 1 ? 'dia' : 'dias'}`;
  return `${span} ${days > 0 ? 'depois' : 'antes'}`;
}
