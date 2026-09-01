/** Formatação pt-PT partilhada. Formatadores `Intl` criados uma vez ao carregar o módulo — construí-los por chamada custa caro. */

export const mznFormatter = new Intl.NumberFormat('pt-PT', {
  style: 'currency',
  currency: 'MZN',
});

export const numberFormatter = new Intl.NumberFormat('pt-PT');

/** Valor monetário sem símbolo — a coluna/etiqueta indica «MZN». */
const amountFormatter = new Intl.NumberFormat('pt-PT', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

/** Diferenças: sinal sempre explícito (`+`/`−` são a informação — creditar a mais vs a menos). */
const signedAmountFormatter = new Intl.NumberFormat('pt-PT', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
  signDisplay: 'exceptZero',
});

const signedMznFormatter = new Intl.NumberFormat('pt-PT', {
  style: 'currency',
  currency: 'MZN',
  signDisplay: 'exceptZero',
});

const dateFormatter = new Intl.DateTimeFormat('pt-PT', {
  day: '2-digit',
  month: 'short',
  year: 'numeric',
});

const shortDateFormatter = new Intl.DateTimeFormat('pt-PT', {
  day: 'numeric',
  month: 'long',
});

export function formatMzn(value: number): string {
  return mznFormatter.format(value);
}

/** Número monetário sem «MZN» (para tabelas onde a moeda vai no cabeçalho/sufixo). */
export function formatAmount(value: number): string {
  return amountFormatter.format(value);
}

/** Diferença sem «MZN», com o sinal sempre à frente: `+1 234,56` · `-1 234,56`. */
export function formatSignedAmount(value: number): string {
  return signedAmountFormatter.format(value);
}

/** Diferença com «MZN», com o sinal sempre à frente. */
export function formatSignedMzn(value: number): string {
  return signedMznFormatter.format(value);
}

export function formatDate(iso: string): string {
  return dateFormatter.format(new Date(`${iso.slice(0, 10)}T00:00:00`));
}

/** "21 a 28 de Junho" a partir de duas datas ISO. */
export function formatInterval(startIso: string, endIso: string): string {
  const start = new Date(`${startIso.slice(0, 10)}T00:00:00`);
  const end = new Date(`${endIso.slice(0, 10)}T00:00:00`);
  if (start.getMonth() === end.getMonth()) {
    return `${start.getDate()} a ${shortDateFormatter.format(end)}`;
  }
  return `${shortDateFormatter.format(start)} a ${shortDateFormatter.format(end)}`;
}
