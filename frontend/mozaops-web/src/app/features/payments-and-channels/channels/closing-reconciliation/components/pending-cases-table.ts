import { ChangeDetectionStrategy, Component, computed, input, output, signal } from '@angular/core';
import { LucideCircleCheck, LucideSearch } from '@lucide/angular';

import { formatAmount, formatDate, numberFormatter } from '../../../../../shared/format';
import { PageFirstScrollDirective } from '../../../../../shared/page-first-scroll';
import type { CaseStatus, CaseType, PendingCase } from '../data/models';
import { MoneyComponent } from './money';

const TYPE_CHIP: Record<CaseType, string> = {
  missing: 'bg-moza-100 text-moza-600',
  mismatch: 'bg-alert-50 text-alert-700',
};
const TYPE_DOT: Record<CaseType, string> = {
  missing: 'bg-moza-500',
  mismatch: 'bg-alert-500',
};
const TYPE_LABEL: Record<CaseType, string> = {
  missing: 'Não creditado',
  mismatch: 'Incorrecto',
};
/** Sombra interior e não `border-l` — ver a nota em STATE_STRIPE, no state-options. */
const TYPE_STRIPE: Record<CaseType, string> = {
  missing: 'shadow-[inset_3px_0_0_var(--color-moza-400)]',
  mismatch: 'shadow-[inset_3px_0_0_var(--color-alert-500)]',
};

const STATUS_LABELS: Record<CaseStatus, string> = {
  pending: 'Pendente',
  'in-review': 'Em análise',
  resolved: 'Regularizado',
};

type StatusFilter = CaseStatus | 'all';

const STATUS_FILTERS: ReadonlyArray<{ id: StatusFilter; label: string }> = [
  { id: 'all', label: 'Todos' },
  { id: 'pending', label: 'Pendentes' },
  { id: 'in-review', label: 'Em análise' },
  { id: 'resolved', label: 'Regularizados' },
];

export interface CasePatch {
  readonly caseId: string;
  readonly patch: { status?: CaseStatus; eTicket?: string | null };
}

/** Fila de trabalho do operador (incorrectos e não creditados) — edita e-Ticket e estado in-line. */
@Component({
  selector: 'app-pending-cases-table',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MoneyComponent, PageFirstScrollDirective, LucideCircleCheck, LucideSearch],
  template: `
    @if (cases().length === 0) {
      <div
        class="flex flex-col items-center gap-3 rounded-2xl border border-gray-100 bg-white py-16 text-center shadow-sm"
      >
        <span
          class="inline-flex size-12 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600"
        >
          <svg lucideCircleCheck [size]="26" [strokeWidth]="1.9"></svg>
        </span>
        <p class="font-semibold text-gray-900">Sem casos para analisar</p>
        <p class="max-w-sm text-sm text-gray-500">
          Todos os fechos conferem ou estão fora de divergência. Não há nada por regularizar.
        </p>
      </div>
    } @else {
      <!-- Sem overflow-hidden, como no cartão irmão dos fechos. Com ele, o cartão
           passava a ser o contentor de scroll da barra de filtros colada, e o
           desvio dela deixava de se contar a partir do topo do ecrã para se contar
           a partir do topo do CARTÃO: a barra fixava-se 60px abaixo dele, por cima
           da lista, e o cabeçalho da tabela tapava-a. Os cantos arredondados
           aguentam-se sozinhos — nenhum filho tem fundo próprio nas pontas. -->
      <div class="@container rounded-2xl border border-gray-100 bg-white shadow-sm">
        <!-- z-20 acima do cabeçalho da tabela — ver a nota na app-reconciliation-table. -->
        <div
          class="sticky top-[calc(var(--app-header-h)+var(--tabs-h))] z-20 rounded-t-2xl border-b border-gray-100 bg-white flex flex-wrap items-center justify-between gap-3 px-4 py-3.5 sm:px-5"
        >
          <div class="inline-flex rounded-xl border border-gray-100 bg-gray-50 p-1">
            @for (filter of statusFilters; track filter.id) {
              @let active = status() === filter.id;
              <button
                type="button"
                (click)="status.set(filter.id)"
                class="inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-semibold transition-colors"
                [class]="
                  active ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-900'
                "
              >
                {{ filter.label }}
                <span class="text-2xs text-gray-400 tabular-nums">
                  {{ n(counts()[filter.id]) }}
                </span>
              </button>
            }
          </div>

          <label
            class="flex min-w-[15rem] flex-1 items-center gap-2.5 rounded-xl border border-gray-100 bg-gray-50 px-3.5 py-2.5 sm:max-w-xs sm:flex-none"
          >
            <svg lucideSearch [size]="16" [strokeWidth]="1.8" class="shrink-0 text-gray-400"></svg>
            <input
              type="search"
              placeholder="Pesquisar caso"
              [value]="query()"
              (input)="query.set($any($event.target).value)"
              class="w-full bg-transparent text-sm text-gray-900 outline-none placeholder:text-gray-400"
            />
          </label>
        </div>

        <!-- relative: ver a nota em reconciliation-table.ts (bloco de contenção). -->
        <div
          [appPageFirstScroll]="scrollAnchor()"
          class="relative max-h-[calc(100dvh-12rem)] min-h-[22rem] overflow-auto"
        >
          <table class="w-full min-w-3xl @4xl:min-w-4xl border-collapse text-sm">
            <!-- Fundo nas células e opaco, e a régua de 3px repetida no cabeçalho —
                 ver a nota igual na app-reconciliation-table. -->
            <thead class="sticky top-0 z-10">
              <tr class="border-y border-gray-100 text-gray-400">
                <th scope="col" [class]="th + ' w-[17rem] py-2.5 pr-3 pl-5 text-left'">
                  POS / Comerciante
                </th>
                <th scope="col" [class]="th + ' hidden px-3 py-2.5 text-right @2xl:table-cell'">
                  Período
                </th>
                <th scope="col" [class]="th + ' px-3 py-2.5 text-right'">Valor SIMO</th>
                <th scope="col" [class]="th + ' px-3 py-2.5 text-right'">Valor Banka</th>
                <th scope="col" [class]="th + ' px-3 py-2.5 text-left'">Tipo</th>
                <th scope="col" [class]="th + ' px-3 py-2.5 text-left'">e-Ticket</th>
                <th scope="col" [class]="th + ' px-3 py-2.5 text-left'">Estado</th>
                <th scope="col" [class]="th + ' hidden px-3 py-2.5 text-left @4xl:table-cell'">
                  Data Reg.
                </th>
              </tr>
            </thead>

            <tbody>
              @for (item of visible(); track item.id) {
                <tr
                  class="border-b border-gray-50 text-gray-600 transition-colors last:border-b-0"
                  [class]="item.status === 'resolved' ? 'bg-emerald-50/40' : 'hover:bg-gray-50/70'"
                >
                  <td class="py-3.5 pr-3 pl-5" [class]="stripe(item)">
                    <div class="font-bold text-gray-900 tabular-nums">{{ item.posId }}</div>
                    <div class="mt-0.5 max-w-48 truncate text-sm text-gray-400">
                      {{ item.merchant }}
                    </div>
                  </td>
                  <td
                    class="hidden px-3 py-3.5 text-right tabular-nums text-gray-400 @2xl:table-cell"
                  >
                    {{ item.period }}
                  </td>
                  <td class="px-3 py-3.5 text-right">
                    <app-money [value]="item.simoAmount" />
                  </td>
                  <td class="px-3 py-3.5 text-right">
                    <app-money [value]="item.type === 'missing' ? null : item.bankaAmount" />
                  </td>
                  <td class="px-3 py-3.5">
                    <span
                      class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-bold whitespace-nowrap"
                      [class]="chip(item)"
                    >
                      <span class="size-1.5 rounded-full" [class]="dot(item)"></span>
                      {{ typeLabel(item) }}
                    </span>
                  </td>
                  <td class="px-3 py-3.5">
                    <!-- Grava ao sair do campo, não a cada tecla: um PATCH por
                         carácter era um pedido por tecla premida. -->
                    <input
                      type="text"
                      [value]="item.eTicket ?? ''"
                      placeholder="—"
                      [attr.aria-label]="'e-Ticket do caso ' + item.posId"
                      (blur)="onETicketBlur(item, $any($event.target).value)"
                      class="w-28 rounded-lg border border-gray-200 bg-white px-2.5 py-1.5 text-xs font-medium text-gray-700 outline-none placeholder:text-gray-300 focus:border-moza-400 focus:ring-2 focus:ring-moza-100"
                    />
                  </td>
                  <td class="px-3 py-3.5">
                    <select
                      [value]="item.status"
                      [attr.aria-label]="'Estado do caso ' + item.posId"
                      (change)="onStatusChange(item, $any($event.target).value)"
                      class="rounded-lg border border-gray-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-gray-700 outline-none focus:border-moza-400 focus:ring-2 focus:ring-moza-100"
                    >
                      @for (option of statusOptions; track option.value) {
                        <option [value]="option.value">{{ option.label }}</option>
                      }
                    </select>
                  </td>
                  <td class="hidden px-3 py-3.5 tabular-nums text-gray-400 @4xl:table-cell">
                    {{ item.resolvedAt ? date(item.resolvedAt) : '—' }}
                  </td>
                </tr>
              } @empty {
                <tr>
                  <td colspan="8" class="px-4 py-10 text-center text-gray-400">
                    Nenhum caso corresponde aos critérios seleccionados.
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>

        <p class="border-t border-gray-100 px-4 py-3.5 text-sm text-gray-400 sm:px-5">
          A mostrar
          <span class="font-semibold text-gray-500 tabular-nums">{{ n(visible().length) }}</span> de
          <span class="font-semibold text-gray-500 tabular-nums">{{ n(cases().length) }}</span>
          casos ·
          <span class="font-semibold text-gray-600 tabular-nums">
            {{ amount(pendingAmount()) }} MZN
          </span>
          por regularizar
        </p>
      </div>
    }
  `,
})
export class PendingCasesTableComponent {
  readonly cases = input.required<readonly PendingCase[]>();
  /** Onde o scroll da página assenta antes de a lista correr — a barra de separadores. */
  readonly scrollAnchor = input<HTMLElement | undefined>(undefined);
  readonly updated = output<CasePatch>();

  /** `bg-gray-50` aqui e não no `<thead>`: é a célula que pinta o fundo de forma fiável. */
  protected readonly th = 'bg-gray-50 text-2xs font-bold tracking-wider uppercase';
  protected readonly statusFilters = STATUS_FILTERS;
  protected readonly statusOptions = Object.entries(STATUS_LABELS).map(([value, label]) => ({
    value,
    label,
  }));

  protected readonly status = signal<StatusFilter>('all');
  protected readonly query = signal('');

  protected readonly counts = computed(() => {
    const cases = this.cases();
    const result: Record<StatusFilter, number> = {
      all: cases.length,
      pending: 0,
      'in-review': 0,
      resolved: 0,
    };
    for (const item of cases) result[item.status] += 1;
    return result;
  });

  protected readonly visible = computed(() => {
    const term = this.query().trim().toLowerCase();
    const status = this.status();
    return this.cases().filter(
      (item) =>
        (status === 'all' || item.status === status) &&
        (!term ||
          item.posId.toLowerCase().includes(term) ||
          item.merchant.toLowerCase().includes(term) ||
          (item.eTicket ?? '').toLowerCase().includes(term)),
    );
  });

  protected readonly pendingAmount = computed(() =>
    this.cases()
      .filter((item) => item.status !== 'resolved')
      .reduce(
        (total, item) => total + Math.abs(item.bankaAmount - item.simoAmount || item.simoAmount),
        0,
      ),
  );

  protected onETicketBlur(item: PendingCase, raw: string): void {
    const value = raw.trim() || null;
    if (value !== item.eTicket) this.updated.emit({ caseId: item.id, patch: { eTicket: value } });
  }

  protected onStatusChange(item: PendingCase, status: string): void {
    this.updated.emit({ caseId: item.id, patch: { status: status as CaseStatus } });
  }

  protected stripe = (item: PendingCase) => TYPE_STRIPE[item.type];
  protected chip = (item: PendingCase) => TYPE_CHIP[item.type];
  protected dot = (item: PendingCase) => TYPE_DOT[item.type];
  protected typeLabel = (item: PendingCase) => TYPE_LABEL[item.type];
  protected amount = formatAmount;
  protected date = formatDate;
  protected n = (value: number) => numberFormatter.format(value);
}
