import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  computed,
  effect,
  inject,
  input,
  linkedSignal,
  output,
  signal,
  viewChild,
  type ElementRef,
} from '@angular/core';
import { NgTemplateOutlet } from '@angular/common';
import { LucideChevronRight, LucideCornerDownRight, LucideSearch, LucideX } from '@lucide/angular';

import {
  formatAmount,
  formatDate,
  formatSignedAmount,
  numberFormatter,
} from '../../../../../../shared/format';
import { DataTableComponent } from '../../../../../../shared/ui/data-table';
import {
  CellIdentityComponent,
  EmptyValueComponent,
  MoneyComponent,
  PillComponent,
  StatusChipComponent,
  TABLE,
} from '../../../../../../shared/ui/table';
import { ReconciliationApi } from '../data/reconciliation-api.service';
import type {
  CaseMatches,
  CasePatch,
  ClosingDetail,
  DetailCounts,
  KeyBreakdown,
  SlaSettings,
} from '../data/models';
import {
  ALL_STATES,
  STATE_CHIP,
  STATE_DOT,
  STATE_LABEL,
  STATE_STRIPE,
  toValidations,
  type StateId,
} from '../data/state-options';
import { KeyDetailPanelComponent } from './key-detail-panel';
import { StateFilterComponent } from './state-filter';

const PER_PAGE = 50;
const SEARCH_DEBOUNCE_MS = 300;
const UNREGISTERED = '—';

const EMPTY_COUNTS: DetailCounts = {
  all: 0,
  match: 0,
  mismatch: 0,
  missing: 0,
  zero: 0,
  duplicated: 0,
};

interface KeyGroup {
  readonly key: string;
  readonly items: ClosingDetail[];
}

/** Junta as linhas contíguas da mesma chave; o servidor já as devolve juntas. */
function groupByKey(items: readonly ClosingDetail[]): KeyGroup[] {
  const groups: KeyGroup[] = [];
  for (const item of items) {
    const current = groups.at(-1);
    if (current && current.key === item.key) current.items.push(item);
    else groups.push({ key: item.key, items: [item] });
  }
  return groups;
}

/**
 * Tabela paginada/filtrada/pesquisada no servidor. A unidade é a CHAVE, não o
 * fecho: chaves com >1 fecho colapsam numa linha-resumo que expande para os
 * fechos individuais. O crédito do Banka é sempre da chave, nunca do fecho.
 */
@Component({
  selector: 'app-reconciliation-table',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    NgTemplateOutlet,
    CellIdentityComponent,
    DataTableComponent,
    EmptyValueComponent,
    KeyDetailPanelComponent,
    MoneyComponent,
    PillComponent,
    StatusChipComponent,
    StateFilterComponent,
    LucideChevronRight,
    LucideCornerDownRight,
    LucideSearch,
    LucideX,
  ],
  template: `
    <app-data-table
      [scrollAnchor]="scrollAnchor()"
      [loading]="loading()"
      [loadingMore]="loadingMore()"
      [hasMore]="hasMore()"
      [hasRows]="items().length > 0"
      [backToTop]="items().length > perPage"
      (loadMore)="page.update((current) => current + 1)"
    >
      <ng-container toolbar>
        <app-state-filter
          [counts]="counts()"
          [selected]="selected()"
          (changed)="selected.set($event)"
        />

        @if (filtered()) {
          <button
            type="button"
            (click)="clearFilters()"
            class="inline-flex shrink-0 items-center gap-1.5 rounded-xl px-2.5 py-2.5 text-sm font-semibold text-gray-500 transition-colors hover:bg-gray-50 hover:text-gray-900"
          >
            <svg lucideX [size]="14" [strokeWidth]="2.4"></svg>
            Limpar filtros
          </button>
        }

        <!-- Primeira a ceder largura quando a barra aperta. -->
        <label
          class="flex w-full min-w-0 items-center gap-2.5 rounded-xl border border-gray-100 bg-gray-50 px-3.5 py-2.5 transition-colors focus-within:border-moza-300 focus-within:bg-white sm:w-auto sm:max-w-[27rem] sm:flex-1"
        >
          <svg lucideSearch [size]="16" [strokeWidth]="1.8" class="shrink-0 text-gray-400"></svg>
          <input
            type="search"
            placeholder="Pesquisar por ID do POS, nome do comerciante ou conta"
            [value]="query()"
            (input)="query.set($any($event.target).value)"
            class="w-full bg-transparent text-sm text-gray-900 outline-none placeholder:text-gray-400"
          />
        </label>

        <p
          class="ml-auto shrink-0 text-sm whitespace-nowrap text-gray-400 transition-opacity"
          [class.opacity-40]="loading()"
        >
          <span class="font-bold text-gray-900 tabular-nums">{{ n(total()) }}</span>
          @if (total() !== counts().all) {
            <span class="tabular-nums"> de {{ n(counts().all) }}</span>
          }
          {{ total() === 1 ? 'fecho' : 'fechos' }}
        </p>
      </ng-container>

      <table [class]="t.table + ' min-w-2xl'">
        <thead [class]="t.thead">
          <tr [class]="t.headRow">
            <th scope="col" [class]="t.thFirst + ' w-[17rem]'">POS / Comerciante</th>
            <th scope="col" [class]="t.thRight">Período</th>
            <th scope="col" [class]="t.thLeft + ' hidden @5xl:table-cell'">Data Fecho</th>
            <th scope="col" [class]="t.thRight">Total SIMO</th>
            <th scope="col" [class]="t.thRight">Total Banka</th>
            <th scope="col" [class]="t.thRight">Diferença</th>
            <th scope="col" [class]="t.thLast">Validação</th>
          </tr>
        </thead>

        <tbody>
          @for (group of groups(); track group.key) {
            @let detail = group.items[0];
            <!-- "Período duplicado" pode vir de três formas: vários fechos na
                 SIMO, vários créditos no Banka (outro período real colidindo
                 em módulo 1000 — ver domain/reconciliation.py), ou as duas ao
                 mesmo tempo. Mostram-se sempre os dois números — 1 de um lado
                 não é motivo para esconder o outro. -->
            @let expandable = detail.validation === 'duplicated';
            @let simoDuplicated = detail.simoClosingsCount > 1;
            @let open = expanded().has(group.key);

            @if (!expandable) {
              <tr
                (click)="opened.set(detail)"
                [class]="
                  t.row +
                  ' ' +
                  (detail.validation === 'zero' ? t.tone.muted + ' ' + t.struck : t.tone.neutral)
                "
              >
                <td [class]="t.tdFirst + ' ' + stripe(detail)">
                  <ng-container
                    [ngTemplateOutlet]="identity"
                    [ngTemplateOutletContext]="{ $implicit: detail }"
                  />
                </td>
                <td [class]="t.tdMuted">{{ detail.period }}</td>
                <td [class]="t.tdMuted + ' hidden text-left @5xl:table-cell'">
                  {{ date(detail.simoClosingDate) }}
                </td>
                <td [class]="t.tdRight"><app-money [value]="detail.simoClosingTotal" /></td>
                <td [class]="t.tdRight"><app-money [value]="detail.bankaClosingTotal" /></td>
                <td [class]="t.tdRight">
                  @if (detail.difference !== null && detail.difference !== 0) {
                    <span class="font-bold text-alert-600">{{ signed(detail.difference) }}</span>
                  } @else {
                    <app-empty-value />
                  }
                </td>
                <td [class]="t.tdLast">
                  <app-status-chip
                    [label]="stateLabel(detail)"
                    [chip]="chip(detail)"
                    [dot]="dot(detail)"
                  />
                </td>
              </tr>
            } @else {
              <!-- Chave duplicada (SIMO ou Banka): linha-resumo, detalhe por baixo. -->
              <tr (click)="opened.set(detail)" [class]="t.row + ' ' + t.tone.attention">
                <td [class]="t.tdFirst + ' ' + stripe(detail)">
                  <div class="flex items-start gap-2">
                    <button
                      type="button"
                      [attr.aria-expanded]="open"
                      [attr.aria-label]="
                        (open ? 'Encolher' : 'Expandir') +
                        ' o detalhe do POS ' +
                        detail.posId +
                        ' no período ' +
                        detail.period +
                        ' — ' +
                        detail.simoClosingsCount +
                        ' na SIMO, ' +
                        detail.bankaMovementsCount +
                        ' no Banka'
                      "
                      (click)="$event.stopPropagation(); toggle(group)"
                      class="mt-0.5 inline-flex size-5 shrink-0 items-center justify-center rounded-md text-amber-600 transition-colors hover:bg-amber-100"
                    >
                      <svg
                        lucideChevronRight
                        [size]="15"
                        [strokeWidth]="2.5"
                        class="transition-transform"
                        [class.rotate-90]="open"
                      ></svg>
                    </button>
                    <div class="min-w-0">
                      <ng-container
                        [ngTemplateOutlet]="identity"
                        [ngTemplateOutletContext]="{ $implicit: detail }"
                      />
                    </div>
                  </div>
                </td>
                <td [class]="t.tdMuted">
                  <span class="inline-flex items-center gap-1.5">
                    {{ detail.period }}
                    <app-pill tone="attention">
                      {{ n(detail.simoClosingsCount) }} SIMO · {{ n(detail.bankaMovementsCount) }}
                      Banka
                    </app-pill>
                  </span>
                </td>
                <td [class]="t.tdMuted + ' hidden text-left @5xl:table-cell'">
                  <!-- Ambígua só se houver mais de um fecho: com um só, a data é certa. -->
                  {{ simoDuplicated ? '—' : date(detail.simoClosingDate) }}
                </td>
                <td [class]="t.tdRight"><app-money [value]="detail.simoKeyTotal" /></td>
                <!-- Banka é da CHAVE, não do fecho. -->
                <td [class]="t.tdRight"><app-money [value]="detail.bankaClosingTotal" /></td>
                <!-- Vazio: os dois lados vêm duplicados, a soma não confere nada. -->
                <td [class]="t.tdRight"><app-empty-value /></td>
                <td [class]="t.tdLast">
                  <app-status-chip
                    [label]="stateLabel(detail)"
                    [chip]="chip(detail)"
                    [dot]="dot(detail)"
                  />
                </td>
              </tr>

              @if (open) {
                @for (item of group.items; track item.id; let position = $index) {
                  <tr (click)="opened.set(item)" [class]="t.subRow">
                    <td [class]="t.subTdFirst + ' shadow-[inset_3px_0_0_var(--color-amber-200)]'">
                      <button
                        type="button"
                        (click)="$event.stopPropagation(); opened.set(item)"
                        class="inline-flex items-center gap-1.5 text-xs font-semibold text-amber-700/80 underline-offset-2 transition-colors hover:text-amber-800 hover:underline focus-visible:underline"
                      >
                        <svg
                          lucideCornerDownRight
                          [size]="13"
                          [strokeWidth]="2"
                          class="text-amber-400"
                        ></svg>
                        SIMO {{ n(position + 1) }}
                      </button>
                    </td>
                    <td [class]="t.subTd + ' text-right text-xs tabular-nums text-gray-300'">
                      {{ item.period }}
                    </td>
                    <td [class]="t.subTd + ' hidden tabular-nums text-gray-400 @5xl:table-cell'">
                      {{ date(item.simoClosingDate) }}
                    </td>
                    <td [class]="t.subTd + ' text-right'">
                      <app-money [value]="item.simoClosingTotal" />
                    </td>
                    <!-- Sem Banka por fecho: já está na linha da chave, acima. -->
                    <td [class]="t.subTd + ' text-right'"><app-empty-value /></td>
                    <td [class]="t.subTd + ' text-right'"><app-empty-value /></td>
                    <td [class]="t.subTd + ' text-xs text-gray-400'">
                      Op. <span class="tabular-nums">{{ item.operationNumber }}</span>
                    </td>
                  </tr>
                }
              }

              @if (open) {
                @let state = breakdowns().get(group.key);
                @if (state === 'loading' || state === undefined) {
                  <tr [class]="t.messageRow + ' bg-amber-50/20'">
                    <td colspan="7" class="px-6 py-2.5 text-xs text-gray-400">
                      A carregar os créditos do Banka…
                    </td>
                  </tr>
                } @else if (state === 'error') {
                  <tr [class]="t.messageRow + ' bg-amber-50/20'">
                    <td colspan="7" class="px-6 py-2.5 text-xs text-alert-600">
                      Não foi possível carregar os créditos do Banka.
                    </td>
                  </tr>
                } @else {
                  @for (movement of state.movements; track movement.id; let position = $index) {
                    <tr (click)="opened.set(detail)" [class]="t.subRow">
                      <td [class]="t.subTdFirst + ' shadow-[inset_3px_0_0_var(--color-amber-200)]'">
                        <span
                          class="inline-flex items-center gap-1.5 text-xs font-semibold text-amber-700/80"
                        >
                          <svg
                            lucideCornerDownRight
                            [size]="13"
                            [strokeWidth]="2"
                            class="text-amber-400"
                          ></svg>
                          Banka {{ n(position + 1) }}
                        </span>
                      </td>
                      <td [class]="t.subTd + ' text-right text-xs text-gray-300'">—</td>
                      <td [class]="t.subTd + ' hidden tabular-nums text-gray-400 @5xl:table-cell'">
                        {{ movement.date ? date(movement.date) : '—' }}
                      </td>
                      <!-- Sem SIMO por crédito: o fecho é o único, já está acima. -->
                      <td [class]="t.subTd + ' text-right'"><app-empty-value /></td>
                      <td [class]="t.subTd + ' text-right'">
                        <app-money [value]="movement.amount" />
                      </td>
                      <td [class]="t.subTd + ' text-right'"><app-empty-value /></td>
                      <td [class]="t.subTd + ' truncate text-xs text-gray-400'">
                        {{ movement.description }}
                      </td>
                    </tr>
                  }
                }
              }
            }
          }

          @if (items().length === 0 && !loading()) {
            <tr>
              <td colspan="7" [class]="t.emptyCell">
                {{
                  selected().length === 0
                    ? 'Nenhuma validação seleccionada — marque pelo menos uma acima.'
                    : 'Nenhum fecho corresponde aos critérios seleccionados.'
                }}
              </td>
            </tr>
          }
        </tbody>
      </table>

      <p footer class="text-sm text-gray-400">
        <span class="font-semibold text-gray-500 tabular-nums">{{ n(items().length) }}</span> de
        <span class="font-semibold text-gray-500 tabular-nums">{{ n(total()) }}</span> fechos
        carregados
      </p>
    </app-data-table>

    <!-- Fora do cartão: o @container faz dele bloco de contenção para
         descendentes fixed, e o painel passaria a medir-se pela tabela. -->
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

    <ng-template #identity let-detail>
      <app-cell-identity
        [primary]="detail.posId"
        [secondary]="detail.merchant === unregistered ? '— sem cadastro' : detail.merchant"
        [secondaryTone]="detail.merchant === unregistered ? 'alert' : 'muted'"
        srLabel="ver os dados da SIMO e do Banka"
        (activated)="opened.set(detail)"
      >
      </app-cell-identity>
    </ng-template>
  `,
})
export class ReconciliationTableComponent {
  private readonly api = inject(ReconciliationApi);

  readonly executionId = input.required<string>();
  /** Só de passagem para o painel de detalhe, que calcula a data limite do caso. */
  readonly settings = input.required<SlaSettings>();
  /** Onde o scroll da página assenta antes de a lista correr — a barra de separadores. */
  readonly scrollAnchor = input<HTMLElement | undefined>(undefined);
  /** Muda sempre que o estado de fechos muda no servidor (uma conciliação) — é o sinal para recarregar. */
  readonly revision = input(0);
  /** Só de passagem: quem muda o caso é o painel, quem o grava é a página. */
  readonly updated = output<CasePatch>();
  readonly reconciled = output<CaseMatches>();

  private readonly table = viewChild.required(DataTableComponent);

  protected readonly perPage = PER_PAGE;
  /** O modelo partilhado das tabelas — ver `shared/ui/table`. */
  protected readonly t = TABLE;
  protected readonly unregistered = UNREGISTERED;

  protected readonly query = signal('');
  private readonly search = signal('');
  /** Estados visíveis — todos por omissão. */
  protected readonly selected = signal<StateId[]>([...ALL_STATES]);

  /** A identidade da consulta — tudo o que dela deriva reinicia via `linkedSignal` quando ela muda. */
  private readonly queryKey = computed(() => {
    const validations = toValidations(this.selected());
    return `${this.executionId()}|${validations?.join(',') ?? 'todos'}|${this.search()}`;
  });

  /**
   * A consulta mais a versão dos dados. Uma conciliação muda o estado de fechos
   * já carregados sem mudar a consulta: recarrega-se tudo desde a primeira
   * página, mas sem voltar ao topo — quem conciliou continua onde estava.
   */
  private readonly dataKey = computed(() => `${this.queryKey()}|${this.revision()}`);

  protected readonly page = linkedSignal({ source: this.dataKey, computation: () => 1 });

  /**
   * NÃO se esvazia ao mudar de consulta, ao contrário do resto que dela deriva:
   * a tabela encolhia durante o pedido e o browser puxava o scroll para cima.
   * As linhas antigas ficam esbatidas até as novas chegarem.
   */
  protected readonly items = signal<readonly ClosingDetail[]>([]);
  protected readonly expanded = linkedSignal<string, ReadonlySet<string>>({
    source: this.dataKey,
    computation: () => new Set<string>(),
  });
  /**
   * Cache por chave dos movimentos Banka de uma chave duplicada só desse lado
   * (1 fecho SIMO, >1 movimento) — não vêm em `items()`, que só traz fechos.
   * Ao contrário dos sub-fechos de uma chave duplicada na SIMO (já em
   * memória), estes têm de ser pedidos ao abrir a linha.
   */
  protected readonly breakdowns = linkedSignal<
    string,
    ReadonlyMap<string, KeyBreakdown | 'loading' | 'error'>
  >({
    source: this.dataKey,
    computation: () => new Map(),
  });
  /** Trava de segurança: uma página vazia encerra a lista, mesmo com `total` inconsistente. */
  private readonly exhausted = linkedSignal({ source: this.dataKey, computation: () => false });

  protected readonly total = signal(0);
  protected readonly counts = signal<DetailCounts>(EMPTY_COUNTS);
  protected readonly loading = signal(true);
  protected readonly loadingMore = signal(false);
  /** Fecho aberto no painel lateral — `null` com o painel fechado. */
  protected readonly opened = signal<ClosingDetail | null>(null);

  protected readonly groups = computed(() => groupByKey(this.items()));
  protected readonly hasMore = computed(
    () => !this.exhausted() && this.items().length < this.total(),
  );
  /** `query` e não `search`: o botão reage à tecla, não espera pelo debounce. */
  protected readonly filtered = computed(
    () => this.query() !== '' || this.selected().length !== ALL_STATES.length,
  );

  constructor() {
    const destroyRef = inject(DestroyRef);

    // Debounce da pesquisa.
    effect((onCleanup) => {
      const value = this.query();
      const timer = setTimeout(() => this.search.set(value.trim()), SEARCH_DEBOUNCE_MS);
      onCleanup(() => clearTimeout(timer));
    });

    // Volta ao topo sempre que a consulta muda — a lista por baixo é outra.
    effect(() => {
      this.queryKey();
      this.table().scrollToTop('instant');
    });

    // Carregamento. Lê `page` e `queryKey`; o `untracked` do resto evita que
    // escrever nos sinais de saída volte a disparar o efeito.
    effect((onCleanup) => {
      const executionId = this.executionId();
      // Lido à parte: com a página já na 1, o `page` não muda ao recarregar, e
      // sem isto o efeito não voltava a correr.
      this.revision();
      const page = this.page();
      const validations = toValidations(this.selected());
      const search = this.search();

      let cancelled = false;
      onCleanup(() => {
        cancelled = true;
      });

      const first = page === 1;
      if (first) this.loading.set(true);
      else this.loadingMore.set(true);

      void this.api
        .listDetails(executionId, {
          page,
          perPage: PER_PAGE,
          validation: validations,
          q: search,
        })
        .then((result) => {
          if (cancelled) return;
          this.items.update((current) => (first ? result.items : [...current, ...result.items]));
          this.total.set(result.total);
          this.counts.set(result.counts);
          if (result.items.length === 0) this.exhausted.set(true);
        })
        .finally(() => {
          if (cancelled) return;
          this.loading.set(false);
          this.loadingMore.set(false);
        });
    });

    destroyRef.onDestroy(() => this.opened.set(null));
  }

  protected toggle(group: KeyGroup): void {
    const key = group.key;
    const opening = !this.expanded().has(key);
    this.expanded.update((current) => {
      const next = new Set(current);
      if (!next.delete(key)) next.add(key);
      return next;
    });

    // Os créditos do Banka pedem-se sempre ao abrir — mesmo quando é só um,
    // para o mostrar ao lado dos fechos SIMO (que nunca se pedem: já estão em
    // `items()`). Esconder o lado que só tem 1 era a mesma confusão que o
    // resumo já não faz.
    if (!opening || this.breakdowns().has(key)) return;
    this.breakdowns.update((current) => new Map(current).set(key, 'loading'));
    void this.api
      .getKeyBreakdown(this.executionId(), key)
      .then((result) =>
        this.breakdowns.update((current) => new Map(current).set(key, result ?? 'error')),
      )
      .catch(() => this.breakdowns.update((current) => new Map(current).set(key, 'error')));
  }

  protected clearFilters(): void {
    this.selected.set([...ALL_STATES]);
    this.query.set('');
    this.search.set('');
  }

  protected stripe = (detail: ClosingDetail) => STATE_STRIPE[detail.validation];
  protected chip = (detail: ClosingDetail) => STATE_CHIP[detail.validation];
  protected dot = (detail: ClosingDetail) => STATE_DOT[detail.validation];
  protected stateLabel = (detail: ClosingDetail) => STATE_LABEL[detail.validation];
  protected date = formatDate;
  protected amount = formatAmount;
  protected signed = formatSignedAmount;
  protected n = (value: number) => numberFormatter.format(value);
}
