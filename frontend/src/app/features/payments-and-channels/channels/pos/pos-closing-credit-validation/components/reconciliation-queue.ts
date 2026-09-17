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
import { DataTableComponent } from '../../../../../../shared/ui/data-table';
import { CellIdentityComponent, MoneyComponent, TABLE } from '../../../../../../shared/ui/table';
import { caseToDetail } from '../data/case-detail';
import { creditedWhen } from '../data/matching';
import type {
  CaseMatches,
  CasePatch,
  ClosingDetail,
  CreditMovement,
  ReconciliationCandidate,
  SlaSettings,
} from '../data/models';
import { KeyDetailPanelComponent } from './key-detail-panel';

interface ProposedPair {
  readonly closing: ClosingDetail;
  readonly movement: CreditMovement;
}

const COLUMNS = 7;

/**
 * O separador «Períodos Duplicados»: as chaves de períodos duplicados em que cada fecho
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
    CellIdentityComponent,
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
            {{ all.length === 1 ? 'período duplicado' : 'períodos duplicados' }}
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

      <table [class]="t.table + ' min-w-3xl'">
        <thead [class]="t.thead">
          <tr [class]="t.headRow">
            <th scope="col" [class]="t.thSelect">
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
            <th scope="col" [class]="t.thLeft">POS / Comerciante</th>
            <th scope="col" [class]="t.thRight">Período</th>
            <th scope="col" [class]="t.thRight">Fechos</th>
            <th scope="col" [class]="t.thRight">Total SIMO</th>
            <th scope="col" [class]="t.thRight">Total Banka</th>
            <th scope="col" [class]="t.thLast + ' w-10'"><span class="sr-only">Ver pares</span></th>
          </tr>
        </thead>

        <tbody>
          @for (candidate of rows(); track candidate.case.id) {
            @let item = candidate.case;
            @let checked = selected().has(item.id);
            @let open = expanded().has(item.id);

            <!-- A linha abre e fecha os pares: é o que se quer ver antes de conciliar. -->
            <tr
              (click)="toggleExpanded(item.id)"
              [class]="t.row + ' ' + t.tone.neutral"
              [class.bg-gray-50/60]="open"
            >
              <!-- A régua verde é a do «confere»: é o estado em que estes fechos ficam. -->
              <td
                [class]="t.tdSelect + ' shadow-[inset_3px_0_0_var(--color-emerald-500)]'"
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
              <td [class]="t.tdLeft">
                <app-cell-identity
                  [primary]="item.posId"
                  [secondary]="item.merchant"
                  srLabel="abrir o caso"
                  (activated)="opened.set(toDetail(item))"
                />
              </td>
              <td [class]="t.tdMuted">{{ item.period }}</td>
              <td [class]="t.tdRight + ' text-gray-900'">{{ n(candidate.closings.length) }}</td>
              <td [class]="t.tdRight"><app-money [value]="item.simoAmount" /></td>
              <!-- O que o Banka creditou para estes fechos — os pares. O que sobra
                   está no aviso, não soma aqui. -->
              <td [class]="t.tdRight"><app-money [value]="pairedTotal(candidate)" /></td>
              <td [class]="t.tdLast + ' text-right'">
                <span
                  class="inline-flex size-7 items-center justify-center rounded-md text-gray-400"
                  [attr.aria-label]="(open ? 'Esconder' : 'Ver') + ' os pares do POS ' + item.posId"
                  [attr.aria-expanded]="open"
                  role="button"
                >
                  <svg
                    lucideChevronDown
                    [size]="15"
                    [strokeWidth]="2.2"
                    class="transition-transform duration-200"
                    [class.rotate-180]="open"
                  ></svg>
                </span>
              </td>
            </tr>

            @if (open) {
              <!-- Os pares que vão ser gravados, lado a lado: o fecho da SIMO à
                   esquerda, o crédito do Banka que o paga à direita. -->
              <tr class="border-b border-gray-100/70 bg-gray-50/60">
                <td></td>
                <td [attr.colspan]="columns - 1" class="pt-1 pr-5 pb-4">
                  <div class="overflow-hidden rounded-xl bg-white ring-1 ring-gray-100">
                    <div
                      class="grid grid-cols-[1fr_2rem_1fr] items-center border-b border-gray-100 bg-gray-50/80 px-4 py-2 text-2xs font-bold tracking-wider text-gray-400 uppercase"
                    >
                      <span>Fecho na SIMO</span>
                      <span></span>
                      <span>Crédito no Banka</span>
                    </div>

                    <ul class="divide-y divide-gray-100">
                      @for (pair of pairsOf(candidate); track pair.closing.id) {
                        <li
                          class="grid grid-cols-[1fr_2rem_1fr] items-center px-4 py-2.5 text-sm tabular-nums"
                        >
                          <span class="flex items-baseline justify-between gap-3">
                            <span class="text-gray-500">
                              {{ date(pair.closing.simoClosingDate) }}
                              <span class="text-xs text-gray-400">
                                · op. {{ pair.closing.operationNumber }}
                              </span>
                            </span>
                            <app-money [value]="pair.closing.simoClosingTotal" />
                          </span>
                          <span class="flex justify-center">
                            <svg
                              lucideLink2
                              [size]="14"
                              [strokeWidth]="2.4"
                              class="text-emerald-500"
                            ></svg>
                          </span>
                          <span class="flex items-baseline justify-between gap-3">
                            <span class="text-gray-500">
                              {{ pair.movement.date ? date(pair.movement.date) : 'Sem data' }}
                              @if (delayOf(pair); as delay) {
                                <span class="text-xs text-gray-400">· {{ delay }}</span>
                              }
                            </span>
                            <app-money [value]="pair.movement.amount" />
                          </span>
                        </li>
                      }
                    </ul>

                    <div
                      class="flex flex-wrap items-center justify-end gap-2 border-t border-gray-100 px-4 py-2.5"
                    >
                      <button
                        type="button"
                        (click)="opened.set(toDetail(item))"
                        class="rounded-lg px-3 py-1.5 text-sm font-semibold text-moza-700 transition-colors hover:bg-moza-50"
                      >
                        Abrir o caso
                      </button>
                    </div>
                  </div>
                </td>
              </tr>
            }
          } @empty {
            <tr>
              <td [attr.colspan]="columns" [class]="t.emptyCell">
                @if (candidates() === null) {
                  A procurar períodos duplicados…
                } @else if (all.length === 0) {
                  Não há períodos duplicados para conciliar com crédito igual.
                } @else {
                  Nenhum período duplicado corresponde à pesquisa.
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
  /** O modelo partilhado das tabelas — ver `shared/ui/table`. */
  protected readonly t = TABLE;

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

  /** O creditado que os pares levam — igual ao total SIMO, porque cada par tem valor igual. */
  protected pairedTotal(candidate: ReconciliationCandidate): number {
    return this.sumOf(this.pairsOf(candidate).map((pair) => pair.movement));
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
