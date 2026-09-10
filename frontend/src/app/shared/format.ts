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
  return dateFormatter.format(parseIsoDate(iso));
}

/**
 * O mesmo para uma `Date` já construída.
 *
 * Existe para não haver a tentação de lhe chamar `toISOString()` primeiro: a
 * meia-noite local a leste de Greenwich é o dia anterior em UTC, e a data
 * saía um dia atrás.
 */
export function formatDateValue(value: Date): string {
  return dateFormatter.format(value);
}

/** Uma data ISO como data local, sem o desvio de fuso que o `new Date(iso)` traz. */
export function parseIsoDate(iso: string): Date {
  return new Date(`${iso.slice(0, 10)}T00:00:00`);
}

/** "1 dia" · "9 dias" — o singular tem de ser singular. */
export function formatDayCount(days: number): string {
  return `${numberFormatter.format(days)} ${days === 1 ? 'dia' : 'dias'}`;
}

/** Dias inteiros de `from` até `to`, ambos tomados como datas locais. */
export function daysBetween(from: Date, to: Date): number {
  const DAY = 24 * 60 * 60 * 1000;
  return Math.round((to.getTime() - from.getTime()) / DAY);
}

/** "21 a 28 de Junho" a partir de duas datas ISO. */
export function formatInterval(startIso: string, endIso: string): string {
  const start = parseIsoDate(startIso);
  const end = parseIsoDate(endIso);
  if (start.getMonth() === end.getMonth()) {
    return `${start.getDate()} a ${shortDateFormatter.format(end)}`;
  }
  return `${shortDateFormatter.format(start)} a ${shortDateFormatter.format(end)}`;
}

/**
 * Percentagens que somam exactamente 100, pelo método do maior resto.
 *
 * Arredondar cada uma por si não fecha: 118, 1 e 16 em 135 somam 99,7%. Aqui
 * arredonda-se tudo para baixo e as décimas em falta vão para quem ficou mais
 * longe do seu valor exacto, portanto a soma fecha por construção.
 */
export function percentageShares(values: readonly number[]): string[] {
  const total = values.reduce((sum, value) => sum + value, 0);
  if (total <= 0) return values.map(() => formatTenths(0));

  const TENTHS = 1000;
  const exact = values.map((value) => (value / total) * TENTHS);
  const shares = exact.map(Math.floor);

  // Cada arredondamento perde menos de uma décima: faltam sempre menos décimas
  // do que valores, logo o ciclo abaixo nunca sai do array.
  const missing = TENTHS - shares.reduce((sum, value) => sum + value, 0);
  const byRemainder = exact
    .map((value, index) => ({ index, remainder: value - Math.floor(value) }))
    .sort((a, b) => b.remainder - a.remainder);

  for (let given = 0; given < missing; given++) shares[byRemainder[given].index]++;

  // Uma parcela que existe mas não chega a uma décima não pode dizer «0%»: isso
  // lê-se como «não há». Vale zero na conta, portanto a soma continua a fechar.
  return shares.map((tenths, index) =>
    tenths === 0 && values[index] > 0 ? '<0,1%' : formatTenths(tenths),
  );
}

function formatTenths(tenths: number): string {
  const percent = tenths / 10;
  const decimals = Number.isInteger(percent) ? 0 : 1;
  return `${percent.toLocaleString('pt-PT', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })}%`;
}
