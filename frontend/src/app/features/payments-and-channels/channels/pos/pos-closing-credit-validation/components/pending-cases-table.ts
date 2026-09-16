import { ChangeDetectionStrategy, Component, computed, input, output, signal } from '@angular/core';
import { LucideChevronRight, LucideCircleCheck, LucideSearch, LucideX } from '@lucide/angular';

import {
  daysBetween,
  formatAmount,
  formatDate,
  formatDateValue,
  formatDayCount,
  formatSignedAmount,
  numberFormatter,
  parseIsoDate,
} from '../../../../../../shared/format';
import {
  DataTableComponent,
  TABLE_CLASS,
  THEAD_CLASS,
} from '../../../../../../shared/ui/data-table';
import {
  CASE_STATUSES,
  CASE_STATUS_BADGE,
  CASE_STATUS_DOT,
  CASE_STATUS_LABEL,
  CASE_STATUS_WAIT,
  OPEN_CASE_STATUSES,
} from '../data/case-status';
import { DUPLICATION_SIDE_LABEL, duplicationSideOf } from '../data/duplication-side';
import type {
  CasePatch,
  CaseStatus,
  CaseType,
  ClosingDetail,
  PendingCase,
  SlaSettings,
} from '../data/models';
import {
  SLA_LABEL,
  SOURCE_LABEL,
  slaAgePhrase,
  slaDotOf,
  slaOf,
  slaPhrase,
  slaToneOf,
  startOfToday,
  type SlaState,
  type SlaView,
} from '../data/sla';
import { CaseStatusFilterComponent } from './case-status-filter';
import { CaseTypeFilterComponent } from './case-type-filter';
import { CaseViewSelectComponent, type CaseView } from './case-view-select';
import { KeyDetailPanelComponent } from './key-detail-panel';
import { MoneyComponent } from './money';
import { SlaFilterComponent } from './sla-filter';

const TYPE_CHIP: Record<CaseType, string> = {
  missing: 'bg-moza-100 text-moza-600',
  mismatch: 'bg-alert-50 text-alert-700',
  duplicated: 'bg-amber-50 text-amber-700',
};
const TYPE_DOT: Record<CaseType, string> = {
  missing: 'bg-moza-500',
  mismatch: 'bg-alert-500',
  duplicated: 'bg-amber-500',
};
const TYPE_LABEL: Record<CaseType, string> = {
  missing: 'Não creditado',
  mismatch: 'Incorrecto',
  duplicated: 'Período duplicado',
};
/** Sombra interior e não `border-l` — ver a nota em STATE_STRIPE, no state-options. */
const TYPE_STRIPE: Record<CaseType, string> = {
  missing: 'shadow-[inset_3px_0_0_var(--color-moza-400)]',
  mismatch: 'shadow-[inset_3px_0_0_var(--color-alert-500)]',
  duplicated: 'shadow-[inset_3px_0_0_var(--color-amber-500)]',
};

const ALL_SLA_STATES: readonly SlaState[] = ['overdue', 'due-soon', 'on-track', 'settled'];
const OPEN_SLA_STATES: readonly SlaState[] = ['overdue', 'due-soon', 'on-track'];

/**
 * Fila de trabalho do operador — só leitura. O estado e o e-Ticket editam-se no
 * painel do caso, que abre ao clicar na linha.
 */
@Component({
  selector: 'app-pending-cases-table',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CaseStatusFilterComponent,
    CaseTypeFilterComponent,
    CaseViewSelectComponent,
    DataTableComponent,
    KeyDetailPanelComponent,
    MoneyComponent,
    SlaFilterComponent,
    LucideChevronRight,
    LucideCircleCheck,
    LucideSearch,
    LucideX,
  ],
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
      <app-data-table [scrollAnchor]="scrollAnchor()">
        <ng-container toolbar>
          <!-- Que casos a lista mostra: em aberto (a fila de trabalho, por
               defeito), regularizados (o histórico) ou todos. Primeiro na barra,
               porque decide o que os filtros ao lado filtram. -->
          <app-case-view-select
            [value]="view()"
            [counts]="viewCounts()"
            (changed)="setView($event)"
          />

          @if (view() !== 'resolved') {
            <app-case-status-filter
              [statuses]="statusOptions()"
              [counts]="statusCounts()"
              [selected]="selectedStatuses()"
              (changed)="selectedStatuses.set($event)"
            />
          }

          <app-case-type-filter
            [counts]="typeCounts()"
            [selected]="selectedTypes()"
            (changed)="selectedTypes.set($event)"
          />

          @if (view() !== 'resolved') {
            <app-sla-filter
              [states]="slaOptions()"
              [counts]="slaCounts()"
              [selected]="selectedSla()"
              (changed)="selectedSla.set($event)"
            />
          }

          <label
            class="flex min-w-[15rem] flex-1 items-center gap-2.5 rounded-xl border border-gray-100 bg-gray-50 px-3.5 py-2.5 transition-colors focus-within:border-moza-300 focus-within:bg-white sm:max-w-xs"
          >
            <svg lucideSearch [size]="16" [strokeWidth]="1.8" class="shrink-0 text-gray-400"></svg>
            <input
              type="search"
              placeholder="Pesquisar por POS, comerciante ou e-Ticket"
              [value]="query()"
              (input)="query.set($any($event.target).value)"
              class="w-full bg-transparent text-sm text-gray-900 outline-none placeholder:text-gray-400"
            />
            @if (query()) {
              <button
                type="button"
                (click)="query.set('')"
                aria-label="Limpar pesquisa"
                class="inline-flex size-4 shrink-0 items-center justify-center rounded-full text-gray-400 hover:bg-gray-200 hover:text-gray-600"
              >
                <svg lucideX [size]="11" [strokeWidth]="2.5"></svg>
              </button>
            }
          </label>
        </ng-container>

        <!-- Oito colunas, e cada célula com uma leitura principal e, no máximo,
             uma nota por baixo. O período vive junto ao POS: numa coluna à
             parte, encostado ao Valor SIMO, lia-se como parte do montante. A
             data de regularização vai para a nota do estado — só existe quando
             o caso está regularizado, e uma coluna de travessões não diz nada. -->
        <table [class]="tableClass + ' min-w-4xl'">
          <thead [class]="theadClass">
            <tr class="border-b border-gray-100 text-gray-400">
              <th scope="col" [class]="th + ' w-[18rem] py-2.5 pr-3 pl-5 text-left'">
                POS / Comerciante
              </th>
              <th scope="col" [class]="th + ' px-3 py-2.5 text-left'">Divergência</th>
              <th scope="col" [class]="th + ' px-3 py-2.5 text-right'">Valor SIMO</th>
              <th scope="col" [class]="th + ' px-3 py-2.5 text-right'">Valor Banka</th>
              <th scope="col" [class]="th + ' px-3 py-2.5 text-right'">Diferença</th>
              <th scope="col" [class]="th + ' py-2.5 pr-3 pl-6 text-left'">Prazo</th>
              <th scope="col" [class]="th + ' px-3 py-2.5 text-left'">
                {{ view() === 'resolved' ? 'Regularizado em' : 'Fase' }}
              </th>
              <th scope="col" [class]="th + ' px-3 py-2.5 text-left'">e-Ticket</th>
              <th scope="col" [class]="th + ' w-8'"><span class="sr-only">Abrir</span></th>
            </tr>
          </thead>

          <tbody>
            @for (item of visible(); track item.id) {
              @let resolved = item.status === 'resolved';
              <tr
                (click)="opened.set(toDetail(item))"
                class="cursor-pointer border-b border-gray-100/70 text-gray-600 transition-colors last:border-b-0 hover:bg-gray-50/70"
              >
                <td class="py-3.5 pr-3 pl-5" [class]="stripe(item)">
                  <div class="flex flex-wrap items-center gap-x-2 gap-y-1">
                    <button
                      type="button"
                      (click)="$event.stopPropagation(); opened.set(toDetail(item))"
                      class="font-bold text-gray-900 tabular-nums underline-offset-2 transition-colors hover:text-moza-600 hover:underline focus-visible:text-moza-600 focus-visible:underline"
                    >
                      {{ item.posId }}
                      <span class="sr-only"> — ver os dados da SIMO e do Banka</span>
                    </button>
                    <span
                      class="rounded-md bg-gray-100 px-1.5 py-0.5 text-2xs font-semibold whitespace-nowrap text-gray-500 tabular-nums"
                      [attr.title]="'Período ' + item.period"
                    >
                      P. {{ item.period }}
                    </span>
                    <!-- Como no "Todos os Fechos": num período duplicado mostram-se
                         sempre os dois números, ao lado do período — 1 de um lado
                         não é motivo para esconder o outro, e «em SIMO e Banka»
                         dizia de que lado era mas não quantos eram. -->
                    @if (item.type === 'duplicated') {
                      <span
                        class="rounded-full bg-amber-500 px-1.5 py-0.5 text-2xs font-bold whitespace-nowrap text-white tabular-nums"
                        [attr.title]="duplicationTitle(item)"
                      >
                        {{ n(item.simoClosingsCount) }} SIMO ·
                        {{ n(item.bankaMovementsCount) }} Banka
                      </span>
                    }
                  </div>
                  <div
                    class="mt-1 max-w-52 truncate text-xs text-gray-400"
                    [attr.title]="item.merchant"
                  >
                    {{ item.merchant }}
                  </div>
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

                <td class="px-3 py-3.5 text-right">
                  <app-money [value]="item.simoAmount" />
                </td>
                <td class="px-3 py-3.5 text-right">
                  <app-money [value]="item.type === 'missing' ? null : item.bankaAmount" />
                </td>
                <td class="px-3 py-3.5 text-right whitespace-nowrap tabular-nums">
                  @let diff = difference(item);
                  @if (diff === null || diff === 0) {
                    <span class="text-gray-300" [attr.title]="diffTitle(item)">—</span>
                  } @else {
                    <span class="font-bold" [class]="resolved ? 'text-gray-400' : 'text-alert-600'">
                      {{ signed(diff) }}
                    </span>
                  }
                </td>

                <td class="py-3.5 pr-3 pl-6">
                  @let sla = slaOf(item);
                  <span
                    class="flex items-center gap-1.5 whitespace-nowrap"
                    [attr.title]="slaTitle(item, sla)"
                  >
                    <span class="size-1.5 shrink-0 rounded-full" [class]="slaDotTone(sla)"></span>
                    <span class="text-xs font-semibold" [class]="slaTone(sla)">
                      {{ slaPhrase(sla) }}
                    </span>
                  </span>
                  <!-- De que lado veio a data que está a contar, e há quanto tempo
                       conta: é o que o operador precisa de saber sem abrir nada. -->
                  <div class="mt-1 pl-3 text-2xs whitespace-nowrap text-gray-400">
                    {{ slaAge(sla) }} · data {{ sourceLabel[item.firstDateSource] }}
                  </div>
                </td>

                <!-- Estado e e-Ticket só se lêem aqui; mudam-se no painel do caso,
                     com «Guardar». Campos soltos na lista gravavam ao sair do
                     campo ou ao escolher uma opção — um toque ao lado e o caso
                     mudava sem ninguém confirmar. -->
                <td class="px-3 py-3.5">
                  @if (view() === 'resolved') {
                    <!-- Na lista dos regularizados o estado é o mesmo em todas as
                         linhas; o que distingue é quando fechou. -->
                    <span
                      class="text-sm font-semibold whitespace-nowrap text-gray-900 tabular-nums"
                    >
                      {{ item.resolvedAt ? date(item.resolvedAt) : '—' }}
                    </span>
                    <div class="mt-1 text-2xs whitespace-nowrap text-gray-400">
                      há {{ dayCount(daysInStatus(item)) }}
                    </div>
                  } @else {
                    <span
                      class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold whitespace-nowrap"
                      [class]="statusBadge[item.status]"
                    >
                      <span class="size-1.5 rounded-full" [class]="statusDot[item.status]"></span>
                      {{ statusLabel[item.status] }}
                    </span>
                    <!-- Há quanto tempo está assim: é o que responde a «submetido
                         à SIMO há quanto tempo?» sem abrir o fecho. Regularizado
                         (na vista de todos), o que interessa é o dia em que fechou. -->
                    <div class="mt-1 pl-1 text-2xs whitespace-nowrap text-gray-400">
                      @if (resolved && item.resolvedAt) {
                        em {{ date(item.resolvedAt) }}
                      } @else {
                        {{ statusWait[item.status] }} {{ dayCount(daysInStatus(item)) }}
                      }
                    </div>
                  }
                </td>

                <td class="px-3 py-3.5 whitespace-nowrap">
                  @if (item.eTicket) {
                    <span class="font-mono text-xs font-semibold text-gray-800">
                      {{ item.eTicket }}
                    </span>
                  } @else {
                    <span class="text-xs text-gray-300">Sem e-Ticket</span>
                  }
                </td>

                <td class="py-3.5 pr-4 pl-1 text-gray-300">
                  <svg lucideChevronRight [size]="16" [strokeWidth]="2.2" aria-hidden="true"></svg>
                </td>
              </tr>
            } @empty {
              <tr>
                <td colspan="9" class="px-4 py-14 text-center">
                  @if (inView().length === 0) {
                    @if (view() !== 'resolved') {
                      <p class="font-semibold text-gray-900">Nenhum caso em aberto</p>
                      <p class="mt-1 text-sm text-gray-500">
                        Todos os casos desta validação estão regularizados.
                      </p>
                    } @else {
                      <p class="font-semibold text-gray-900">Ainda não há casos regularizados</p>
                      <p class="mt-1 text-sm text-gray-500">
                        Os casos aparecem aqui quando, no painel do caso, passam a «Regularizado».
                      </p>
                    }
                  } @else {
                    <p class="text-gray-400">Nenhum caso corresponde aos filtros seleccionados.</p>
                  }
                </td>
              </tr>
            }
          </tbody>
        </table>

        <p footer class="text-sm text-gray-400">
          A mostrar
          <span class="font-semibold text-gray-500 tabular-nums">{{ n(visible().length) }}</span> de
          <span class="font-semibold text-gray-500 tabular-nums">{{ n(inView().length) }}</span>
          @switch (view()) {
            @case ('resolved') {
              casos regularizados
            }
            @default {
              {{ view() === 'open' ? 'casos em aberto' : 'casos' }} ·
              <span class="font-semibold text-gray-600 tabular-nums">
                {{ amount(pendingAmount()) }} MZN
              </span>
              por regularizar
            }
          }
        </p>
      </app-data-table>

      <!-- Fora do cartão, como no "Todos os Fechos" — mesma razão: o
           @container faz de contentor de posicionamento para o painel fixed. -->
      @if (opened(); as detail) {
        <app-key-detail-panel
          [executionId]="executionId()"
          [detail]="detail"
          [settings]="settings()"
          (updated)="updated.emit($event)"
          (closed)="opened.set(null)"
        />
      }
    }
  `,
})
export class PendingCasesTableComponent {
  readonly cases = input.required<readonly PendingCase[]>();
  readonly executionId = input.required<string>();
  readonly settings = input.required<SlaSettings>();
  /** Onde o scroll da página assenta antes de a lista correr — a barra de separadores. */
  readonly scrollAnchor = input<HTMLElement | undefined>(undefined);
  readonly updated = output<CasePatch>();

  /** O caso aberto no painel lateral — o mesmo painel do "Todos os Fechos". */
  protected readonly opened = signal<ClosingDetail | null>(null);

  /** `bg-gray-50` aqui e não no `<thead>`: é a célula que pinta o fundo de forma fiável. */
  protected readonly th = 'bg-gray-50 text-2xs font-bold tracking-wider uppercase';
  protected readonly tableClass = TABLE_CLASS;
  protected readonly theadClass = THEAD_CLASS;

  /** A fila de trabalho abre por defeito — é para isso que se vem a este separador. */
  protected readonly view = signal<CaseView>('open');

  /** Os estados e os prazos que existem na vista: em aberto não há «Regularizado». */
  protected readonly statusOptions = computed(() =>
    this.view() === 'all' ? CASE_STATUSES : OPEN_CASE_STATUSES,
  );
  protected readonly slaOptions = computed<readonly SlaState[]>(() =>
    this.view() === 'all' ? ALL_SLA_STATES : OPEN_SLA_STATES,
  );

  protected readonly selectedStatuses = signal<CaseStatus[]>([...OPEN_CASE_STATUSES]);
  protected readonly query = signal('');
  protected readonly selectedTypes = signal<CaseType[]>(['mismatch', 'duplicated', 'missing']);
  protected readonly selectedSla = signal<SlaState[]>([...OPEN_SLA_STATES]);

  /** Mudar de vista repõe os filtros de estado e prazo: as opções deixam de ser as mesmas. */
  protected setView(view: CaseView): void {
    this.view.set(view);
    this.selectedStatuses.set([...this.statusOptions()]);
    this.selectedSla.set([...this.slaOptions()]);
  }

  /** Fixado à montagem: uma tabela aberta não muda de dia a meio de um clique. */
  protected readonly today = startOfToday();
  protected readonly sourceLabel = SOURCE_LABEL;
  protected readonly statusLabel = CASE_STATUS_LABEL;
  protected readonly statusWait = CASE_STATUS_WAIT;
  protected readonly statusBadge = CASE_STATUS_BADGE;
  protected readonly statusDot = CASE_STATUS_DOT;

  /** Dias no estado actual — o relógio recomeça a cada mudança de estado. */
  protected daysInStatus = (item: PendingCase): number =>
    daysBetween(parseIsoDate(item.statusSince), this.today);

  /**
   * O prazo de cada caso, numa passagem só — e não uma função por célula, que
   * voltaria a fazer a conta a cada detecção de alterações.
   */
  private readonly slaByCase = computed(() => {
    const settings = this.settings();
    const today = this.today;
    return new Map(this.cases().map((item) => [item.id, slaOf(item, settings, today)]));
  });

  protected readonly openCases = computed(() =>
    this.cases().filter((item) => item.status !== 'resolved'),
  );
  protected readonly resolvedCases = computed(() =>
    this.cases().filter((item) => item.status === 'resolved'),
  );
  protected readonly inView = computed(() => {
    switch (this.view()) {
      case 'open':
        return this.openCases();
      case 'resolved':
        return this.resolvedCases();
      default:
        return this.cases();
    }
  });

  protected readonly viewCounts = computed<Record<CaseView, number>>(() => ({
    all: this.cases().length,
    open: this.openCases().length,
    resolved: this.resolvedCases().length,
  }));

  protected readonly slaCounts = computed(() => {
    const result: Record<SlaState, number> = {
      overdue: 0,
      'due-soon': 0,
      'on-track': 0,
      settled: 0,
    };
    const sla = this.slaByCase();
    for (const item of this.inView()) result[sla.get(item.id)!.state] += 1;
    return result;
  });

  protected readonly statusCounts = computed(() => {
    const result: Record<CaseStatus, number> = {
      pending: 0,
      'in-review-internal': 0,
      'in-review-simo': 0,
      resolved: 0,
    };
    for (const item of this.inView()) result[item.status] += 1;
    return result;
  });

  protected readonly typeCounts = computed(() => {
    const result: Record<CaseType, number> = { mismatch: 0, duplicated: 0, missing: 0 };
    for (const item of this.inView()) result[item.type] += 1;
    return result;
  });

  protected readonly visible = computed(() => {
    const term = this.query().trim().toLowerCase();
    const filtersApply = this.view() !== 'resolved';
    const statuses = this.selectedStatuses();
    const types = this.selectedTypes();
    const slaStates = this.selectedSla();
    const sla = this.slaByCase();
    const rows = this.inView().filter(
      (item) =>
        (!filtersApply || statuses.includes(item.status)) &&
        types.includes(item.type) &&
        (!filtersApply || slaStates.includes(sla.get(item.id)!.state)) &&
        (!term ||
          item.posId.toLowerCase().includes(term) ||
          item.merchant.toLowerCase().includes(term) ||
          (item.eTicket ?? '').toLowerCase().includes(term)),
    );

    // Em aberto, o mais urgente primeiro: mais dias em atraso à cabeça, o que
    // ainda tem folga no fim. Regularizados, o mais recente primeiro — e, na
    // vista de todos, depois de todos os que ainda estão em aberto.
    return rows.sort((a, b) => {
      const aResolved = a.status === 'resolved';
      const bResolved = b.status === 'resolved';
      if (aResolved !== bResolved) return aResolved ? 1 : -1;
      if (aResolved) return (b.resolvedAt ?? '').localeCompare(a.resolvedAt ?? '');
      return sla.get(a.id)!.remaining - sla.get(b.id)!.remaining || a.posId.localeCompare(b.posId);
    });
  });

  protected readonly pendingAmount = computed(() =>
    this.openCases().reduce(
      (total, item) => total + Math.abs(item.bankaAmount - item.simoAmount || item.simoAmount),
      0,
    ),
  );

  /**
   * O caso é da chave inteira, não de um fecho — não há um `id`/data/nº de
   * operação de fecho para dar. Servem só para abrir o mesmo painel lateral;
   * o `closingType` no cabeçalho corrige-se sozinho assim que o painel carrega
   * os fechos reais da chave (ver `key-detail-panel.ts`).
   */
  protected toDetail = (item: PendingCase): ClosingDetail => ({
    id: item.id,
    posId: item.posId,
    merchant: item.merchant,
    accountNumber: item.accountNumber,
    period: item.period,
    key: item.key,
    simoClosingDate: '',
    operationNumber: 0,
    simoClosingTotal: item.simoAmount,
    simoKeyTotal: item.simoAmount,
    closingDescription: null,
    bankaCreditDate: null,
    bankaClosingTotal: item.bankaAmount,
    closingType: 'n.a',
    validation: item.type,
    difference: item.bankaAmount - item.simoAmount,
    simoClosingsCount: item.simoClosingsCount,
    bankaMovementsCount: item.bankaMovementsCount,
  });

  protected slaOf = (item: PendingCase): SlaView => this.slaByCase().get(item.id)!;

  // A frase e a cor são as mesmas no painel de detalhe: vivem no `data/sla.ts`
  // para as duas leituras não divergirem.
  protected slaPhrase = slaPhrase;
  protected slaAge = slaAgePhrase;
  protected slaTone = slaToneOf;
  protected slaDotTone = slaDotOf;

  /** Ao passar o rato: donde conta o prazo, e até quando. */
  protected slaTitle(item: PendingCase, sla: SlaView): string {
    const side = SOURCE_LABEL[item.firstDateSource];
    return (
      `${SLA_LABEL[sla.state]}. Conta desde ${this.date(item.firstDate)} — ` +
      `a primeira data da chave, do lado ${side === 'SIMO' ? 'da' : 'do'} ${side}. ` +
      `Data limite ${this.dateValue(sla.deadline)}.`
    );
  }

  protected stripe = (item: PendingCase) => TYPE_STRIPE[item.type];
  protected chip = (item: PendingCase) => TYPE_CHIP[item.type];
  protected dot = (item: PendingCase) => TYPE_DOT[item.type];
  protected typeLabel = (item: PendingCase) => TYPE_LABEL[item.type];

  /** Ao passar o rato: os números por extenso, e de que lado está a duplicação. */
  protected duplicationTitle(item: PendingCase): string {
    const closings = `${this.n(item.simoClosingsCount)} ${item.simoClosingsCount === 1 ? 'fecho' : 'fechos'} na SIMO`;
    const movements = `${this.n(item.bankaMovementsCount)} ${item.bankaMovementsCount === 1 ? 'movimento' : 'movimentos'} no Banka`;
    const side = duplicationSideOf(item.simoClosingsCount, item.bankaMovementsCount);
    return side
      ? `${closings}, ${movements} — duplicado em ${DUPLICATION_SIDE_LABEL[side]}.`
      : `${closings}, ${movements}.`;
  }

  /**
   * Banka menos SIMO, como no "Todos os Fechos". Não creditado é o valor SIMO
   * inteiro em falta. Duplicado não tem diferença: com um dos lados a somar
   * vários fechos, a conta não confere nada — mesma regra da outra tabela.
   */
  protected difference(item: PendingCase): number | null {
    if (item.type === 'duplicated') return null;
    if (item.type === 'missing') return -item.simoAmount;
    return item.bankaAmount - item.simoAmount;
  }

  protected diffTitle(item: PendingCase): string | null {
    return item.type === 'duplicated'
      ? 'Sem diferença num período duplicado: um dos lados soma vários fechos.'
      : null;
  }

  protected amount = formatAmount;
  protected signed = formatSignedAmount;
  protected date = formatDate;
  protected dateValue = formatDateValue;
  protected dayCount = formatDayCount;
  protected n = (value: number) => numberFormatter.format(value);
}
