/**
 * De que lado vem uma chave `duplicated` — vários fechos na SIMO, vários
 * movimentos no Banka, ou os dois. Fonte única desta regra: sem ela, cada
 * sítio que mostra `duplicated` (a tabela, os casos pendentes, o painel de
 * detalhe) inventava a sua própria forma de o dizer.
 */
export type DuplicationSide = 'simo' | 'banka' | 'both';

export function duplicationSideOf(
  simoClosingsCount: number,
  bankaMovementsCount: number,
): DuplicationSide | null {
  const simo = simoClosingsCount > 1;
  const banka = bankaMovementsCount > 1;
  if (simo && banka) return 'both';
  if (simo) return 'simo';
  if (banka) return 'banka';
  return null;
}

export const DUPLICATION_SIDE_LABEL: Record<DuplicationSide, string> = {
  simo: 'SIMO',
  banka: 'Banka',
  both: 'SIMO e Banka',
};
