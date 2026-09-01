import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  computed,
  effect,
  inject,
  input,
  linkedSignal,
  signal,
  viewChild,
  type ElementRef,
} from '@angular/core';
import { NgTemplateOutlet } from '@angular/common';
import {
  LucideArrowUp,
  LucideChevronRight,
  LucideCornerDownRight,
  LucideLoaderCircle,
  LucideSearch,
  LucideX,
} from '@lucide/angular';

import { formatDate, formatSignedAmount, numberFormatter } from '../../../../../shared/format';
import { PageFirstScrollDirective } from '../../../../../shared/page-first-scroll';
import { ReconciliationApi } from '../data/reconciliation-api.service';
import type { ClosingDetail, DetailCounts } from '../data/models';
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
import { MoneyComponent } from './money';
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

/** Gradiente de 1px no fundo (não `line-through`): risca a linha inteira, colunas vazias incluídas. */
const STRUCK_ROW =
  'bg-[linear-gradient(currentColor,currentColor)] bg-[length:100%_1px] bg-center bg-no-repeat';

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
    KeyDetailPanelComponent,
    MoneyComponent,
    PageFirstScrollDirective,
    StateFilterComponent,
    LucideArrowUp,
    LucideChevronRight,
    LucideCornerDownRight,
    LucideLoaderCircle,
    LucideSearch,
    LucideX,
  ],
  template: `
    <!-- Sem overflow-hidden: cortaria o painel do filtro quando a tabela é curta. -->
    <div class="@container rounded-2xl border border-gray-100 bg-white shadow-sm">
      <!-- Cola por baixo dos separadores: o filtro e a pesquisa são o que mais se
           mexe enquanto se percorre a lista, e saíam do ecrã logo à primeira.

           z-20 e não z-10: a barra cria contexto de empilhamento, portanto tudo o
           que está dentro dela — o painel do filtro incluído — fica travado neste
           nível, por muito alto que lá dentro se peça. Empatada a 10 com o
           cabeçalho da tabela, decidia a ordem no DOM e o cabeçalho ganhava: a
           linha «Todos os estados» do painel ficava tapada por ele, e com ela a
           única forma de marcar ou desmarcar tudo de uma vez.

           Não colide com os separadores, que também são z-20: a barra cola-se
           exactamente onde eles acabam (--tabs-h), nunca chegam a sobrepor-se. -->
      <div
        class="sticky top-[calc(var(--app-header-h)+var(--tabs-h))] z-20 rounded-t-2xl border-b border-gray-100 bg-white flex flex-wrap items-center gap-2.5 px-4 py-3.5 sm:px-5"
      >
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

        <!-- Primeira a ceder largura quando a barra aperta, para não empurrar o resto. -->
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
      </div>

      <!-- O limite de altura conta com o que divide o ecrã com a lista, e não é um
           número à parte: se o cartão for mais alto do que o que sobra, no fim do
           scroll da página o cartão passa por baixo da barra de filtros colada e
           ela come o topo do cabeçalho da tabela — que fica a parecer mais uma
           faixa da lista. Media-se 27px de 37 nos últimos 10px de scroll.

           Daí subtrair, além do que a barra de filtros ocupa (~70px), do rodapé
           do cartão (~60px) e da margem inferior da página (~13px), também os
           desvios onde ela própria cola: a barra do menu e os separadores. Assim
           a conta continua certa abaixo do lg, onde a barra do menu existe e o
           desvio quase duplica.

           E min-h para a caixa não desabar quando um filtro deixa três linhas: a
           página encurtava, o scroll era puxado para cima e perdia-se o sítio.
           relative é bloco de contenção — sem ele um descendente absolute escapa
           ao recorte e estica a altura da PÁGINA à da tabela. -->
      <div
        #scrollBox
        [appPageFirstScroll]="scrollAnchor()"
        class="relative max-h-[calc(100dvh-var(--app-header-h)-var(--tabs-h)-9.5rem)] min-h-[22rem] overflow-auto transition-opacity"
        [class.opacity-50]="loading()"
      >
        <table class="w-full min-w-2xl border-collapse text-sm">
          <!-- O fundo vai nas células, não aqui: num grupo de linhas, e com bordas
               colapsadas, não se pode contar com ele. E opaco — estava a 95% com
               backdrop-blur, feito para se ver através, e via-se mesmo: as réguas
               de estado e os fundos âmbar das chaves passavam por trás da faixa. -->
          <thead class="sticky top-0 z-10">
            <!-- Só border-b. Com border-y havia duas riscas de 1px encostadas — a
                 de baixo da barra de filtros e a de cima desta linha, da mesma cor
                 — e duas riscas juntas lêem-se como um sulco entre as duas divs.
                 As outras tabelas do módulo já eram só border-b. -->
            <tr class="border-b border-gray-100 text-gray-400">
              <th scope="col" [class]="th + ' w-[17rem] py-2.5 pr-3 pl-5 text-left'">
                POS / Comerciante
              </th>
              <th scope="col" [class]="th + ' px-3 py-2.5 text-right'">Período</th>
              <th scope="col" [class]="th + ' hidden px-3 py-2.5 text-left @5xl:table-cell'">
                Data Fecho
              </th>
              <th scope="col" [class]="th + ' px-3 py-2.5 text-right'">Total SIMO</th>
              <th scope="col" [class]="th + ' px-3 py-2.5 text-right'">Total Banka</th>
              <th scope="col" [class]="th + ' px-3 py-2.5 text-right'">Diferença</th>
              <th scope="col" [class]="th + ' px-3 py-2.5 text-left'">Estado</th>
            </tr>
          </thead>

          <tbody>
            @for (group of groups(); track group.key) {
              @let detail = group.items[0];
              @let duplicated = detail.validation === 'duplicated';
              @let compared = !duplicated;
              @let open = expanded().has(group.key);

              @if (group.items.length === 1) {
                <tr
                  (click)="opened.set(detail)"
                  class="cursor-pointer border-b border-gray-50 transition-colors last:border-b-0 hover:bg-gray-50/70"
                  [class]="
                    detail.validation === 'zero' ? 'text-gray-400 ' + struckRow : 'text-gray-600'
                  "
                >
                  <td class="py-3.5 pr-3 pl-5" [class]="stripe(detail)">
                    <ng-container
                      [ngTemplateOutlet]="identity"
                      [ngTemplateOutletContext]="{ $implicit: detail }"
                    />
                  </td>
                  <td class="px-3 py-3.5 text-right tabular-nums text-gray-400">
                    {{ detail.period }}
                  </td>
                  <td class="hidden px-3 py-3.5 tabular-nums text-gray-400 @5xl:table-cell">
                    {{ date(detail.simoClosingDate) }}
                  </td>
                  <td class="px-3 py-3.5 text-right">
                    <app-money [value]="detail.simoClosingTotal" />
                  </td>
                  <td class="px-3 py-3.5 text-right">
                    <app-money [value]="compared ? detail.bankaClosingTotal : null" />
                  </td>
                  <td class="px-3 py-3.5 text-right tabular-nums">
                    @if (compared && detail.difference !== null && detail.difference !== 0) {
                      <span class="font-bold text-alert-600">
                        {{ signed(detail.difference) }}
                      </span>
                    } @else {
                      <span class="text-gray-300">—</span>
                    }
                  </td>
                  <td class="px-3 py-3.5">
                    <ng-container
                      [ngTemplateOutlet]="stateChip"
                      [ngTemplateOutletContext]="{ $implicit: detail }"
                    />
                  </td>
                </tr>
              } @else {
                <!-- Vários fechos no período: linha da CHAVE (total agregado), fechos por baixo. -->
                <tr
                  (click)="opened.set(detail)"
                  class="cursor-pointer border-b border-gray-50 bg-amber-50/40 text-gray-600 transition-colors last:border-b-0 hover:bg-amber-50/70"
                >
                  <td class="py-3.5 pr-3 pl-5" [class]="stripe(detail)">
                    <div class="flex items-start gap-2">
                      <button
                        type="button"
                        [attr.aria-expanded]="open"
                        [attr.aria-label]="
                          (open ? 'Encolher' : 'Expandir') +
                          ' os ' +
                          group.items.length +
                          ' fechos do POS ' +
                          detail.posId +
                          ' no período ' +
                          detail.period
                        "
                        (click)="$event.stopPropagation(); toggle(group.key)"
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
                  <td class="px-3 py-3.5 text-right tabular-nums text-gray-400">
                    <span class="inline-flex items-center gap-1.5">
                      {{ detail.period }}
                      <span
                        class="rounded-full bg-amber-500 px-1.5 py-0.5 text-2xs font-bold whitespace-nowrap text-white"
                      >
                        {{ n(group.items.length) }} fechos
                      </span>
                    </span>
                  </td>
                  <td class="hidden px-3 py-3.5 text-gray-300 @5xl:table-cell">—</td>
                  <td class="px-3 py-3.5 text-right">
                    <app-money [value]="detail.simoKeyTotal" />
                  </td>
                  <!-- Banka é da CHAVE, não do fecho: mostra-se aqui, não nas linhas por baixo. -->
                  <td class="px-3 py-3.5 text-right">
                    <app-money [value]="detail.bankaClosingTotal" />
                  </td>
                  <!-- Vazio: os dois lados vêm duplicados, a soma não confere nada. -->
                  <td class="px-3 py-3.5 text-right">
                    <span class="text-gray-300">—</span>
                  </td>
                  <td class="px-3 py-3.5">
                    <ng-container
                      [ngTemplateOutlet]="stateChip"
                      [ngTemplateOutletContext]="{ $implicit: detail }"
                    />
                  </td>
                </tr>

                @if (open) {
                  @for (item of group.items; track item.id; let position = $index) {
                    <tr
                      (click)="opened.set(item)"
                      class="cursor-pointer border-b border-gray-50 bg-amber-50/20 text-gray-500 transition-colors last:border-b-0 hover:bg-amber-50/50"
                    >
                      <td class="py-2.5 pr-3 pl-6 shadow-[inset_3px_0_0_var(--color-amber-200)]">
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
                          Fecho {{ n(position + 1) }}
                        </button>
                      </td>
                      <td class="px-3 py-2.5 text-right text-xs tabular-nums text-gray-300">
                        {{ item.period }}
                      </td>
                      <td class="hidden px-3 py-2.5 tabular-nums text-gray-400 @5xl:table-cell">
                        {{ date(item.simoClosingDate) }}
                      </td>
                      <td class="px-3 py-2.5 text-right">
                        <app-money [value]="item.simoClosingTotal" />
                      </td>
                      <!-- Sem Banka por fecho: já está na linha da chave, acima. -->
                      <td class="px-3 py-2.5 text-right">
                        <span class="text-gray-300">—</span>
                      </td>
                      <td class="px-3 py-2.5 text-right">
                        <span class="text-gray-300">—</span>
                      </td>
                      <td class="px-3 py-2.5 text-xs text-gray-400">
                        Op. <span class="tabular-nums">{{ item.operationNumber }}</span>
                      </td>
                    </tr>
                  }
                }
              }
            }

            @if (items().length === 0 && !loading()) {
              <tr>
                <td colspan="7" class="px-4 py-12 text-center text-gray-400">
                  {{
                    selected().length === 0
                      ? 'Nenhum estado seleccionado — marque pelo menos um acima.'
                      : 'Nenhum fecho corresponde aos critérios seleccionados.'
                  }}
                </td>
              </tr>
            }
          </tbody>
        </table>

        <!-- Sentinela do scroll infinito — fora da tabela para não sujar o tbody. -->
        <div #sentinel aria-hidden="true" class="h-px"></div>

        @if (loadingMore()) {
          <p class="flex items-center justify-center gap-2 py-4 text-sm text-gray-400">
            <svg lucideLoaderCircle [size]="15" [strokeWidth]="2" class="animate-spin"></svg>
            A carregar mais fechos…
          </p>
        }
        @if (!hasMore() && items().length > 0) {
          <p class="py-4 text-center text-sm text-gray-300">Fim da lista</p>
        }
      </div>

      <div
        class="flex flex-wrap items-center justify-between gap-3 border-t border-gray-100 px-4 py-3.5 sm:px-5"
      >
        <p class="text-sm text-gray-400">
          <span class="font-semibold text-gray-500 tabular-nums">{{ n(items().length) }}</span> de
          <span class="font-semibold text-gray-500 tabular-nums">{{ n(total()) }}</span> fechos
          carregados
        </p>

        <!-- Escape para quem não quer rolar 12 mil linhas para voltar ao princípio. -->
        @if (items().length > perPage) {
          <button
            type="button"
            (click)="scrollToTop()"
            class="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-semibold text-gray-500 transition-colors hover:bg-gray-50 hover:text-gray-900"
          >
            <svg lucideArrowUp [size]="14" [strokeWidth]="2.2"></svg>
            Voltar ao topo
          </button>
        }
      </div>
    </div>

    <!-- Fora do cartão de propósito: o cartão é @container, e container-type faz
         dele bloco de contenção para descendentes fixed. Lá dentro, este painel
         deixava de se medir pela janela e passava a medir-se pela tabela. -->
    @if (opened(); as detail) {
      <app-key-detail-panel
        [executionId]="executionId()"
        [detail]="detail"
        (closed)="opened.set(null)"
      />
    }

    <!-- O POS ID é um botão focável; um tr não é, e role="button" destruiria a semântica. -->
    <ng-template #identity let-detail>
      <button
        type="button"
        (click)="$event.stopPropagation(); opened.set(detail)"
        class="font-bold text-gray-900 tabular-nums underline-offset-2 transition-colors hover:text-moza-600 hover:underline focus-visible:text-moza-600 focus-visible:underline"
      >
        {{ detail.posId }}
        <span class="sr-only"> — ver os dados da SIMO e do Banka</span>
      </button>
      <div class="mt-0.5 max-w-56 truncate text-sm text-gray-400">
        @if (detail.merchant === unregistered) {
          <span class="text-alert-600">— sem cadastro</span>
        } @else {
          {{ detail.merchant }}
        }
      </div>
    </ng-template>

    <ng-template #stateChip let-detail>
      <span
        class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-bold whitespace-nowrap"
        [class]="chip(detail)"
      >
        <span class="size-1.5 rounded-full" [class]="dot(detail)"></span>
        {{ stateLabel(detail) }}
      </span>
    </ng-template>
  `,
})
export class ReconciliationTableComponent {
  private readonly api = inject(ReconciliationApi);

  readonly executionId = input.required<string>();
  /** Onde o scroll da página assenta antes de a lista correr — a barra de separadores. */
  readonly scrollAnchor = input<HTMLElement | undefined>(undefined);

  private readonly scrollBox = viewChild<ElementRef<HTMLElement>>('scrollBox');
  private readonly sentinel = viewChild<ElementRef<HTMLElement>>('sentinel');

  protected readonly perPage = PER_PAGE;
  protected readonly unregistered = UNREGISTERED;
  protected readonly struckRow = STRUCK_ROW;
  /** `bg-gray-50` aqui e não no `<thead>`: é a célula que pinta o fundo de forma fiável. */
  protected readonly th = 'bg-gray-50 text-2xs font-bold tracking-wider uppercase';

  protected readonly query = signal('');
  private readonly search = signal('');
  /** Estados visíveis — todos por omissão. */
  protected readonly selected = signal<StateId[]>([...ALL_STATES]);

  /** A identidade da consulta — tudo o que dela deriva reinicia via `linkedSignal` quando ela muda. */
  private readonly queryKey = computed(() => {
    const validations = toValidations(this.selected());
    return `${this.executionId()}|${validations?.join(',') ?? 'todos'}|${this.search()}`;
  });

  private readonly page = linkedSignal({ source: this.queryKey, computation: () => 1 });

  /**
   * NÃO se esvazia ao mudar de consulta, ao contrário do resto que deriva dela.
   * Esvaziar encolhia a tabela de cinquenta linhas para zero durante o pedido; a
   * página ficava mais curta do que a posição do scroll e o browser era obrigado
   * a puxá-la para cima, de volta aos gráficos. As linhas antigas ficam à vista,
   * esbatidas, até as novas chegarem e as substituírem — é para isso que serve o
   * `opacity-50` na caixa.
   */
  protected readonly items = signal<readonly ClosingDetail[]>([]);
  protected readonly expanded = linkedSignal<string, ReadonlySet<string>>({
    source: this.queryKey,
    computation: () => new Set<string>(),
  });
  /** Trava de segurança: uma página vazia encerra a lista, mesmo com `total` inconsistente. */
  private readonly exhausted = linkedSignal({ source: this.queryKey, computation: () => false });

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
      this.scrollBox()?.nativeElement.scrollTo({ top: 0 });
    });

    // Carregamento. Lê `page` e `queryKey`; o `untracked` do resto evita que
    // escrever nos sinais de saída volte a disparar o efeito.
    effect((onCleanup) => {
      const executionId = this.executionId();
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
        .listDetails(executionId, { page, perPage: PER_PAGE, validation: validations, q: search })
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

    // Pede a página seguinte ao ver a sentinela. `items().length === 0` evita pedir
    // a página 2 antes da 1 chegar, quando um filtro esvazia a lista.
    effect((onCleanup) => {
      if (!this.hasMore() || this.loading() || this.loadingMore() || this.items().length === 0) {
        return;
      }
      const node = this.sentinel()?.nativeElement;
      if (!node) return;

      const observer = new IntersectionObserver(
        (entries) => {
          if (entries[0].isIntersecting) this.page.update((current) => current + 1);
        },
        { root: this.scrollBox()?.nativeElement ?? null, rootMargin: '320px' },
      );
      observer.observe(node);
      onCleanup(() => observer.disconnect());
    });

    destroyRef.onDestroy(() => this.opened.set(null));
  }

  protected toggle(key: string): void {
    this.expanded.update((current) => {
      const next = new Set(current);
      if (!next.delete(key)) next.add(key);
      return next;
    });
  }

  protected clearFilters(): void {
    this.selected.set([...ALL_STATES]);
    this.query.set('');
    this.search.set('');
  }

  protected scrollToTop(): void {
    this.scrollBox()?.nativeElement.scrollTo({ top: 0, behavior: 'smooth' });
  }

  protected stripe = (detail: ClosingDetail) => STATE_STRIPE[detail.validation];
  protected chip = (detail: ClosingDetail) => STATE_CHIP[detail.validation];
  protected dot = (detail: ClosingDetail) => STATE_DOT[detail.validation];
  protected stateLabel = (detail: ClosingDetail) => STATE_LABEL[detail.validation];
  protected date = formatDate;
  protected signed = formatSignedAmount;
  protected n = (value: number) => numberFormatter.format(value);
}
