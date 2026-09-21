import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';

import { formatAmount } from '../format';

/**
 * O modelo das tabelas de lista — o desenho de «Todos os Fechos», para todas as
 * automações terem as linhas iguais.
 *
 * Duas partes. As **classes** de tabela, cabeçalho, linha e célula, para usar
 * em `[class]` nos `<table>`, `<tr>`, `<th>` e `<td>` — as linhas não viram
 * componentes, porque um componente dentro de `<tbody>` parte a tabela, e há
 * linhas que agrupam e expandem. E as **peças de célula** (identidade,
 * montante, etiqueta de estado, pastilha), que se põem dentro de um `<td>`.
 *
 * Uma tabela típica, dentro de um `app-data-table`, com `protected readonly t = TABLE;`:
 *
 * ```html
 * <table [class]="t.table + ' min-w-4xl'">
 *   <thead [class]="t.thead">
 *     <tr [class]="t.headRow">
 *       <th scope="col" [class]="t.thFirst + ' w-[17rem]'">POS / Comerciante</th>
 *       <th scope="col" [class]="t.thRight">Total</th>
 *       <th scope="col" [class]="t.thLast">Estado</th>
 *     </tr>
 *   </thead>
 *   <tbody>
 *     <tr (click)="open(item)" [class]="t.row + ' ' + t.tone.neutral">
 *       <td [class]="t.tdFirst + ' ' + stripe(item)">
 *         <app-cell-identity [primary]="item.posId" [secondary]="item.merchant" />
 *       </td>
 *       <td [class]="t.tdRight"><app-money [value]="item.total" /></td>
 *       <td [class]="t.tdLast"><app-status-chip [label]="…" [chip]="…" [dot]="…" /></td>
 *     </tr>
 *   </tbody>
 * </table>
 * ```
 */

/** A largura mínima fica a cargo de quem usa: depende das colunas que tem. */
export const TABLE_CLASS = 'w-full border-collapse text-sm';

/** Colado ao topo da caixa. O fundo vai nas células, nunca aqui — ver o data-table. */
export const THEAD_CLASS = 'sticky top-0 z-10';

/**
 * Fundo e risca vão na CÉLULA, nunca no `<thead>` nem na `<tr>`: com
 * `border-collapse`, o que é pintado pela tabela não acompanha um cabeçalho
 * colado, e vê-se a tremer ao rolar. Daí a risca ser um `box-shadow` e não uma
 * `border`.
 */
const TH =
  'bg-gray-50 shadow-[inset_0_-1px_0_var(--color-gray-100)] py-2.5 text-2xs font-bold tracking-wider uppercase';
/** A primeira e a última coluna têm o recuo do cartão; as do meio, `px-3`. */
const EDGE_FIRST = 'pr-3 pl-5';
const EDGE_LAST = 'pr-5 pl-3';
const CELL_Y = 'py-3.5';

export const TABLE = {
  table: TABLE_CLASS,
  thead: THEAD_CLASS,
  /** A risca do fundo vem das células — ver `TH`. */
  headRow: 'text-gray-400',

  thFirst: `${TH} ${EDGE_FIRST} text-left`,
  /** A coluna das caixas de selecção, quando a tabela as tem — vem antes da primeira. */
  thSelect: `${TH} w-12 pr-1 pl-5 text-left`,
  thLeft: `${TH} px-3 text-left`,
  thRight: `${TH} px-3 text-right`,
  thLast: `${TH} ${EDGE_LAST} text-left`,

  /** A linha: clicável, risca fina entre linhas. O tom (fundo, cor do texto) vem de `tone`. */
  row: 'cursor-pointer border-b border-gray-50 transition-colors last:border-b-0',
  tone: {
    neutral: 'text-gray-600 hover:bg-gray-50/70',
    /** O que pede atenção sem ser erro — os períodos duplicados, por exemplo. */
    attention: 'bg-amber-50/40 text-gray-600 hover:bg-amber-50/70',
    /** O que não pede nada — fechos zerados, por exemplo. */
    muted: 'text-gray-400 hover:bg-gray-50/70',
    /** Marcado sem ser problema — linhas duplicadas no ficheiro, por exemplo. */
    marked: 'bg-rose-50/40 text-gray-600 hover:bg-rose-50/70',
  },
  /**
   * Risca a linha inteira, colunas vazias incluídas — um registo que não conta.
   * Gradiente de 1px no fundo e não `line-through`, que só risca o texto.
   */
  struck:
    'bg-[linear-gradient(currentColor,currentColor)] bg-[length:100%_1px] bg-center bg-no-repeat',
  /** Linha de detalhe por baixo de uma linha que expande. */
  subRow:
    'cursor-pointer border-b border-gray-50 bg-amber-50/20 text-gray-500 transition-colors last:border-b-0 hover:bg-amber-50/50',
  /** Linha de detalhe de uma linha marcada (`tone.marked`). */
  subRowMarked:
    'cursor-pointer border-b border-gray-50 bg-rose-50/20 text-gray-500 transition-colors last:border-b-0 hover:bg-rose-50/50',
  /** Linha de aviso sem clique — a lista vazia, «a carregar…». */
  messageRow: 'border-b border-gray-50 last:border-b-0',

  tdFirst: `${CELL_Y} ${EDGE_FIRST}`,
  tdSelect: `${CELL_Y} pr-1 pl-5`,
  tdLeft: `${CELL_Y} px-3`,
  tdRight: `${CELL_Y} px-3 text-right tabular-nums`,
  /** Número secundário — o período, uma data. */
  tdMuted: `${CELL_Y} px-3 text-right tabular-nums text-gray-400`,
  tdLast: `${CELL_Y} ${EDGE_LAST}`,
  /** Nas linhas de detalhe a célula é mais baixa, e a primeira recua um pouco mais. */
  subTdFirst: 'py-2.5 pr-3 pl-6',
  subTd: 'px-3 py-2.5',

  /** A nota por baixo da leitura principal de uma célula. */
  note: 'mt-1 text-2xs whitespace-nowrap text-gray-400',
  /** A célula única da linha de lista vazia. */
  emptyCell: 'px-4 py-12 text-center text-gray-400',
} as const;

// ─── Peças de célula ─────────────────────────────────────────────────────────

/**
 * A primeira coluna: o identificador a negrito, que abre o registo, e o nome
 * por baixo. O que a linha tiver a mais (uma marca, um aviso) entra por projecção.
 */
@Component({
  selector: 'app-cell-identity',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <!-- Um botão, e não só a linha clicável: um <tr> não é focável. -->
    <button
      type="button"
      (click)="$event.stopPropagation(); activated.emit()"
      class="font-bold text-gray-900 tabular-nums underline-offset-2 transition-colors hover:text-moza-600 hover:underline focus-visible:text-moza-600 focus-visible:underline"
    >
      {{ primary() }}
      @if (srLabel()) {
        <span class="sr-only"> — {{ srLabel() }}</span>
      }
    </button>
    @if (secondary(); as text) {
      <div
        class="mt-0.5 max-w-56 truncate text-sm"
        [class]="secondaryTone() === 'alert' ? 'text-alert-600' : 'text-gray-400'"
        [attr.title]="text"
      >
        {{ text }}
      </div>
    }
    <ng-content />
  `,
})
export class CellIdentityComponent {
  readonly primary = input.required<string>();
  readonly secondary = input<string | null>(null);
  readonly secondaryTone = input<'muted' | 'alert'>('muted');
  /** O que o botão faz, para leitores de ecrã. */
  readonly srLabel = input<string | null>(null);
  readonly activated = output<void>();
}

/** Um montante em MZN, ou travessão quando não há valor — `null` é ausência, não zero. */
@Component({
  selector: 'app-money',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @let v = value();
    @if (v === null) {
      <span class="text-gray-300">—</span>
    } @else {
      <span
        class="font-semibold whitespace-nowrap tabular-nums"
        [class]="muted() ? 'text-gray-500' : 'text-gray-900'"
      >
        {{ amount(v) }}<span class="ml-1 text-[0.7em] font-normal text-gray-400">MZN</span>
      </span>
    }
  `,
})
export class MoneyComponent {
  readonly value = input.required<number | null>();
  readonly muted = input(false);
  protected amount = formatAmount;
}

/** Célula sem valor — o travessão cinzento, igual em todas as tabelas. */
@Component({
  selector: 'app-empty-value',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<span class="text-gray-300">—</span>`,
})
export class EmptyValueComponent {}

/**
 * A etiqueta de estado de uma linha: ponto e texto numa pastilha de cor. As
 * cores são de quem usa (cada automação tem os seus estados).
 */
@Component({
  selector: 'app-status-chip',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <span
      class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-bold whitespace-nowrap"
      [class]="chip()"
    >
      <span class="size-1.5 rounded-full" [class]="dot()"></span>
      {{ label() }}
    </span>
  `,
})
export class StatusChipComponent {
  readonly label = input.required<string>();
  /** Fundo e texto — `bg-emerald-50 text-emerald-700`, por exemplo. */
  readonly chip = input.required<string>();
  readonly dot = input.required<string>();
}

const PILL_TONE = {
  attention: 'bg-amber-500 text-white',
  neutral: 'bg-gray-100 text-gray-500',
  violet: 'bg-violet-50 text-violet-700',
  rose: 'bg-rose-50 text-rose-700',
} as const;

/**
 * Pastilha pequena ao lado de um valor — «6 SIMO · 8 Banka», «Crédito sem
 * fecho». O texto (e um ícone, se houver) entra por projecção.
 */
@Component({
  selector: 'app-pill',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <span
      class="inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-2xs font-bold whitespace-nowrap tabular-nums"
      [class]="toneClass()"
    >
      <ng-content />
    </span>
  `,
})
export class PillComponent {
  readonly tone = input<keyof typeof PILL_TONE>('neutral');
  protected readonly toneClass = computed(() => PILL_TONE[this.tone()]);
}
