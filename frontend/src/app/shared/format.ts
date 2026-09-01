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

/**
 * Percentagens que somam exactamente 100.
 *
 * Arredondar cada uma por si não fecha, e não é azar: 118, 1 e 16 em 135 dão
 * 87,4%, 0,74% e 11,85%, que arredondadas isoladamente somam 99,7. Num ecrã de
 * conciliação, três números que não fecham fazem duvidar de tudo o resto.
 *
 * Método do maior resto: arredonda-se tudo para baixo, e as décimas que faltam
 * vão para quem ficou mais longe do seu valor exacto — que é quem mais direito
 * tem a elas. A soma fecha por construção, não por sorte.
 *
 * Trabalha-se em décimas de ponto percentual, e a décima só se mostra quando
 * não é zero: uma fatia de 0,7% não pode aparecer como «1%», que é o dobro, e
 * 87% não precisa de virar «87,0%» para provar nada.
 */
export function percentageShares(values: readonly number[]): string[] {
  const total = values.reduce((sum, value) => sum + value, 0);
  if (total <= 0) return values.map(() => formatTenths(0));

  const TENTHS = 1000;
  const exact = values.map((value) => (value / total) * TENTHS);
  const shares = exact.map(Math.floor);

  // Cada arredondamento para baixo perde menos de uma décima, portanto faltam
  // sempre menos décimas do que valores — não há aqui volta a dar.
  const missing = TENTHS - shares.reduce((sum, value) => sum + value, 0);
  const byRemainder = exact
    .map((value, index) => ({ index, remainder: value - Math.floor(value) }))
    .sort((a, b) => b.remainder - a.remainder);

  for (let given = 0; given < missing; given++) shares[byRemainder[given].index]++;

  // Uma parcela que existe mas não chega a uma décima não pode aparecer como
  // «0%»: num ecrã de conciliação isso lê-se como «não há», e há — são 2599,00
  // contra 543 milhões. Vale zero décimas na conta, e a soma dos outros continua
  // a fechar 100; o que muda é só a palavra com que se mostra.
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
