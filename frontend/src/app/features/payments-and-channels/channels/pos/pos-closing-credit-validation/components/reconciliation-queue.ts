import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
  linkedSignal,
  output,
  signal,
} from '@angular/core';
import {
  LucideCheckCheck,
  LucideChevronDown,
  LucideLink2,
  LucideLoaderCircle,
  LucideSearch,
  LucideX,
} from '@lucide/angular';

import { formatAmount, formatDate, numberFormatter } from '../../../../../../shared/format';
import { CheckboxComponent } from '../../../../../../shared/ui/checkbox';
import {
  DataTableComponent,
  TABLE_CLASS,
  THEAD_CLASS,
} from '../../../../../../shared/ui/data-table';
import { caseToDetail } from '../data/case-detail';
import { creditedWhen, withinPeriod } from '../data/matching';
import type {
  CaseMatches,
  CasePatch,
  ClosingDetail,
  CreditMovement,
  ReconciliationCandidate,
  SlaSettings,
} from '../data/models';
import { KeyDetailPanelComponent } from './key-detail-panel';
import { MoneyComponent } from './money';

interface ProposedPair {
  readonly closing: ClosingDetail;
  readonly movement: CreditMovement;
}

const COLUMNS = 8;

/**
 * O separador «Conciliações»: as chaves de períodos duplicados em que cada fecho
 * tem no Banka um crédito com o mesmo valor — no mesmo formato de «Todos os
 * Fechos», com pesquisa, selecção e a acção de conciliar as escolhidas de uma vez.
 *
 * Só mostra: a lista vem da página (que a pede ao servidor sempre que os casos
 * mudam) e os pares a gravar voltam para ela, que é quem chama a API.
 */
@Component({
  selector: 'app-reconciliation-queue',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CheckboxComponent,
    DataTableComponent,
    KeyDetailPanelComponent,
    MoneyComponent,
    LucideCheckCheck,
    LucideChevronDown,
    LucideLink2,
    LucideLoaderCircle,
    LucideSearch,
    LucideX,
  ],
  template: `
    @let all = candidates() ?? [];

    <app-data-table [loading]="candidates() === null" [hasRows]="rows().length > 0">
      <ng-container toolbar>
        <label
          class="flex w-full min-w-0 items-center gap-2.5 rounded-xl border border-gray-100 bg-gray-50 px-3.5 py-2.5 transition-colors focus-within:border-moza-300 focus-within:bg-white sm:w-auto sm:max-w-[27rem] sm:flex-1"
        >
          <svg lucideSearch [size]="16" [strokeWidth]="1.8" class="shrink-0 text-gray-400"></svg>
          <input
            type="search"
            placeholder="Pesquisar por ID do POS ou comerciante"
            [value]="query()"
            (input)="query.set($any($event.target).value)"
            class="w-full bg-transparent text-sm text-gray-900 outline-none placeholder:text-gray-400"
          />
        </label>

        @if (query() !== '') {
          <button
            type="button"
            (click)="query.set('')"
            class="inline-flex shrink-0 items-center gap-1.5 rounded-xl px-2.5 py-2.5 text-sm font-semibold text-gray-500 transition-colors hover:bg-gray-50 hover:text-gray-900"
          >
            <svg lucideX [size]="14" [strokeWidth]="2.4"></svg>
            Limpar pesquisa
          </button>
        }

        <div class="ml-auto flex shrink-0 items-center gap-3">
          <p class="text-sm whitespace-nowrap text-gray-400">
            <span class="font-bold text-gray-900 tabular-nums">{{ n(rows().length) }}</span>
            @if (rows().length !== all.length) {
              <span class="tabular-nums"> de {{ n(all.length) }}</span>
            }
            {{ all.length === 1 ? 'chave' : 'chaves' }}
          </p>

          <!-- A acção vive na barra, como os filtros: fica à vista com a lista a
               correr, e diz sempre quantas chaves e fechos vai gravar. -->
          <button
            type="button"
            (click)="confirm()"
            [disabled]="selectedRows().length === 0 || busy()"
            class="inline-flex items-center gap-1.5 rounded-xl bg-moza-700 px-3.5 py-2.5 text-sm font-semibold whitespace-nowrap text-white shadow-sm transition-colors hover:bg-moza-800 disabled:cursor-not-allowed disabled:bg-gray-200 disabled:text-gray-400 disabled:shadow-none"
          >
            @if (busy()) {
              <svg lucideLoaderCircle [size]="15" [strokeWidth]="2.2" class="animate-spin"></svg>
              A conciliar…
            } @else {
              <svg lucideCheckCheck [size]="15" [strokeWidth]="2.4"></svg>
              Conciliar {{ n(selectedRows().length) }}
              <span class="font-normal opacity-80">
                · {{ n(selectedClosings()) }} {{ selectedClosings() === 1 ? 'fecho' : 'fechos' }}
              </span>
            }
          </button>
        </div>
      </ng-container>

      <table [class]="tableClass + ' min-w-2xl'">
        <thead [class]="theadClass">
          <tr class="border-b border-gray-100 text-gray-400">
            <th scope="col" [class]="th + ' w-12 py-2.5 pr-1 pl-5 text-left'">
              <label class="inline-flex cursor-pointer">
                <app-checkbox
                  ariaLabel="Seleccionar todas"
                  [checked]="masterState() === 'on'"
                  [indeterminate]="masterState() === 'partial'"
                  [disabled]="rows().length === 0"
                  (toggled)="toggleAll()"
                />
              </label>
            </th>
            <th scope="col" [class]="th + ' w-[17rem] py-2.5 pr-3 text-left'">POS / Comerciante</th>
            <th scope="col" [class]="th + ' px-3 py-2.5 text-right'">Período</th>
            <th scope="col" [class]="th + ' px-3 py-2.5 text-right'">Fechos</th>
            <th scope="col" [class]="th + ' px-3 py-2.5 text-right'">Total SIMO</th>
            <th scope="col" [class]="th + ' px-3 py-2.5 text-right'">Total Banka</th>
            <th scope="col" [class]="th + ' px-3 py-2.5 text-right'">Crédito sem fecho</th>
            <th scope="col" [class]="th + ' w-10'"><span class="sr-only">Pares</span></th>
          </tr>
        </thead>

        <tbody>
          @for (candidate of rows(); track candidate.case.id) {
            @let item = candidate.case;
            @let checked = selected().has(item.id);
            @let open = expanded().has(item.id);
            <tr
              (click)="opened.set(toDetail(item))"
              class="cursor-pointer border-b border-gray-100/70 text-gray-600 transition-colors hover:bg-gray-50/70"
            >
              <!-- A régua verde é a do «confere»: é o estado em que estes fechos ficam. -->
              <td
                class="py-3.5 pr-1 pl-5 shadow-[inset_3px_0_0_var(--color-emerald-500)]"
                (click)="$event.stopPropagation()"
              >
                <label class="inline-flex cursor-pointer">
                  <app-checkbox
                    [ariaLabel]="'Conciliar o POS ' + item.posId + ', período ' + item.period"
                    [checked]="checked"
                    (toggled)="toggle(item.id)"
                  />
                </label>
              </td>
              <td class="py-3.5 pr-3">
                <span class="block font-bold text-gray-900 tabular-nums">{{ item.posId }}</span>
                <span class="mt-0.5 block max-w-56 truncate text-sm text-gray-400">
                  {{ item.merchant }}
                </span>
              </td>
              <td class="px-3 py-3.5 text-right text-gray-400 tabular-nums">{{ item.period }}</td>
              <td class="px-3 py-3.5 text-right tabular-nums">
                {{ n(candidate.closings.length) }}
              </td>
              <td class="px-3 py-3.5 text-right"><app-money [value]="item.simoAmount" /></td>
              <td class="px-3 py-3.5 text-right"><app-money [value]="item.bankaAmount" /></td>
              <!-- Dinheiro do Banka que nenhum fecho leva. Os fechos conciliam-se na
                   mesma, mas o caso fica aberto para alguém o analisar. -->
              <td class="px-3 py-3.5 text-right whitespace-nowrap">
                @let leftovers = leftoversOf(candidate);
                @if (leftovers.length > 0) {
                  <span
                    class="inline-flex items-center gap-1.5 rounded-full bg-amber-50 px-2 py-0.5 text-xs font-bold text-amber-700 tabular-nums"
                  >
                    {{ amount(sumOf(leftovers)) }}
                    <span class="font-normal text-amber-600/80">MZN</span>
                  </span>
                } @else {
                  <span class="text-gray-300">—</span>
                }
              </td>
              <td class="py-3.5 pr-4 text-right" (click)="$event.stopPropagation()">
                <button
                  type="button"
                  (click)="toggleExpanded(item.id)"
                  [attr.aria-expanded]="open"
                  [attr.aria-label]="(open ? 'Esconder' : 'Ver') + ' os pares do POS ' + item.posId"
                  class="inline-flex size-7 items-center justify-center rounded-md text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-900"
                >
                  <svg
                    lucideChevronDown
                    [size]="15"
                    [strokeWidth]="2.2"
                    class="transition-transform duration-200"
                    [class.rotate-180]="open"
                  ></svg>
                </button>
              </td>
            </tr>

            @if (open) {
              <!-- Os pares que vão ser gravados, antes de se carregar no botão. -->
              <tr class="border-b border-gray-100/70 bg-gray-50/40">
                <td></td>
                <td [attr.colspan]="columns - 1" class="py-2.5 pr-5">
                  <ul class="space-y-1">
                    @for (pair of pairsOf(candidate); track pair.closing.id) {
                      <li
                        class="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-gray-500 tabular-nums"
                      >
                        <span>
                          Fecho de {{ date(pair.closing.simoClosingDate) }} ·
                          <b class="font-semibold text-gray-800">
                            {{ amount(pair.closing.simoClosingTotal) }}
                          </b>
                        </span>
                        <svg
                          lucideLink2
                          [size]="12"
                          [strokeWidth]="2.4"
                          class="text-emerald-500"
                        ></svg>
                        <span>
                          Crédito de
                          {{ pair.movement.date ? date(pair.movement.date) : 'data desconhecida' }}
                        </span>
                        @if (delayOf(pair); as delay) {
                          <span class="text-gray-400">· {{ delay }}</span>
                        }
                      </li>
                    }
                    @for (movement of leftoversOf(candidate); track movement.id) {
                      <li
                        class="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-amber-800 tabular-nums"
                      >
                        <span>
                          Crédito de
                          {{ movement.date ? date(movement.date) : 'data desconhecida' }} ·
                          <b class="font-semibold">{{ amount(movement.amount) }}</b>
                        </span>
                        <span>— sem fecho na SIMO; o caso fica aberto para o analisar.</span>
                      </li>
                    }
                    @for (movement of laterOf(candidate); track movement.id) {
                      <li
                        class="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-gray-400 tabular-nums"
                      >
                        <span>
                          Crédito de {{ date(movement.date!) }} ·
                          <b class="font-semibold">{{ amount(movement.amount) }}</b>
                        </span>
                        <span>— depois do intervalo; é do seguinte, não conta.</span>
                      </li>
                    }
                  </ul>
                </td>
              </tr>
            }
          } @empty {
            <tr>
              <td [attr.colspan]="columns" class="px-4 py-12 text-center text-gray-400">
                @if (candidates() === null) {
                  A procurar conciliações…
                } @else if (all.length === 0) {
                  Não há chaves para conciliar com crédito igual.
                } @else {
                  Nenhuma chave corresponde à pesquisa.
                }
              </td>
            </tr>
          }
        </tbody>
      </table>
    </app-data-table>

    <!-- Fora do cartão, como nas outras vistas: o painel é fixed e mede-se pela janela. -->
    @if (opened(); as detail) {
      <app-key-detail-panel
        [executionId]="executionId()"
        [detail]="detail"
        [settings]="settings()"
        (updated)="updated.emit($event)"
        (reconciled)="reconciled.emit($event)"
        (closed)="opened.set(null)"
      />
    }
  `,
})
export class ReconciliationQueueComponent {
  readonly executionId = input.required<string>();
  /** As chaves a conciliar; `null` enquanto a página ainda as está a pedir. */
  readonly candidates = input.required<readonly ReconciliationCandidate[] | null>();
  /** Só de passagem para o painel, que calcula a data limite do caso. */
  readonly settings = input.required<SlaSettings>();
  /** A página está a gravar uma conciliação — o botão espera. */
  readonly busy = input(false);

  /** Os pares das chaves seleccionadas — quem os grava é a página. */
  readonly reconciledMany = output<readonly CaseMatches[]>();
  /** Só de passagem, do painel para a página. */
  readonly updated = output<CasePatch>();
  readonly reconciled = output<CaseMatches>();

  protected readonly opened = signal<ClosingDetail | null>(null);
  protected readonly query = signal('');
  protected readonly expanded = signal<ReadonlySet<string>>(new Set());

  protected readonly rows = computed(() => {
    const search = this.query().trim().toLowerCase();
    const all = this.candidates() ?? [];
    if (!search) return all;
    return all.filter(
      (candidate) =>
        candidate.case.posId.includes(search) ||
        candidate.case.merchant.toLowerCase().includes(search),
    );
  });

  /** Todas vêm seleccionadas: são pares de valor exactamente igual, e o caso comum é conciliar todas. */
  protected readonly selected = linkedSignal<ReadonlySet<string>>(
    () => new Set((this.candidates() ?? []).map((candidate) => candidate.case.id)),
  );

  /** Só o que está à vista entra: pesquisar é também escolher o que se concilia. */
  protected readonly selectedRows = computed(() =>
    this.rows().filter((candidate) => this.selected().has(candidate.case.id)),
  );
  protected readonly selectedClosings = computed(() =>
    this.selectedRows().reduce((total, candidate) => total + candidate.closings.length, 0),
  );
  protected readonly masterState = computed<'on' | 'off' | 'partial'>(() => {
    const count = this.selectedRows().length;
    if (count === 0) return 'off';
    return count === this.rows().length ? 'on' : 'partial';
  });

  protected readonly columns = COLUMNS;
  protected readonly tableClass = TABLE_CLASS;
  protected readonly theadClass = THEAD_CLASS;
  /** `bg-gray-50` aqui e não no `<thead>`: é a célula que pinta o fundo de forma fiável. */
  protected readonly th = 'bg-gray-50 text-2xs font-bold tracking-wider uppercase';

  protected toggle(caseId: string): void {
    this.selected.update((current) => {
      const next = new Set(current);
      if (!next.delete(caseId)) next.add(caseId);
      return next;
    });
  }

  protected toggleAll(): void {
    const visible = this.rows().map((candidate) => candidate.case.id);
    const selectAll = this.masterState() !== 'on';
    this.selected.update((current) => {
      const next = new Set(current);
      for (const id of visible) {
        if (selectAll) next.add(id);
        else next.delete(id);
      }
      return next;
    });
  }

  protected toggleExpanded(caseId: string): void {
    this.expanded.update((current) => {
      const next = new Set(current);
      if (!next.delete(caseId)) next.add(caseId);
      return next;
    });
  }

  protected confirm(): void {
    if (this.busy()) return;
    const items: CaseMatches[] = this.selectedRows().map((candidate) => ({
      caseId: candidate.case.id,
      matches: candidate.suggestedMatches,
    }));
    if (items.length > 0) this.reconciledMany.emit(items);
  }

  protected pairsOf(candidate: ReconciliationCandidate): ProposedPair[] {
    const closings = new Map(candidate.closings.map((closing) => [closing.id, closing]));
    const movements = new Map(candidate.movements.map((movement) => [movement.id, movement]));
    return candidate.suggestedMatches.flatMap((match) => {
      const closing = closings.get(match.closingId);
      const movement = movements.get(match.movementId);
      return closing && movement ? [{ closing, movement }] : [];
    });
  }

  /** Os créditos da chave que nenhum fecho leva, do intervalo — ver `settles_case` no servidor. */
  protected leftoversOf(candidate: ReconciliationCandidate): CreditMovement[] {
    return this.unusedOf(candidate).filter((movement) =>
      withinPeriod(movement, candidate.periodEnd),
    );
  }

  /** Os que sobram mas são de depois do último dia — do intervalo seguinte, não contam. */
  protected laterOf(candidate: ReconciliationCandidate): CreditMovement[] {
    return this.unusedOf(candidate).filter(
      (movement) => !withinPeriod(movement, candidate.periodEnd),
    );
  }

  private unusedOf(candidate: ReconciliationCandidate): CreditMovement[] {
    const used = new Set(candidate.suggestedMatches.map((match) => match.movementId));
    return candidate.movements.filter((movement) => !used.has(movement.id));
  }

  protected sumOf = (movements: readonly CreditMovement[]): number =>
    movements.reduce((total, movement) => total + movement.amount, 0);

  protected delayOf = (pair: ProposedPair): string | null =>
    creditedWhen(pair.closing.simoClosingDate, pair.movement.date);

  protected toDetail = caseToDetail;
  protected amount = formatAmount;
  protected date = formatDate;
  protected n = (value: number) => numberFormatter.format(value);
}
