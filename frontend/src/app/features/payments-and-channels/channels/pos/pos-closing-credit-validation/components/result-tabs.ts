import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  computed,
  inject,
  input,
  linkedSignal,
  output,
  signal,
  viewChild,
  type ElementRef,
} from '@angular/core';
import {
  LucideArrowLeft,
  LucideArrowRight,
  LucideArrowUp,
  LucideLink2,
  LucideTriangleAlert,
} from '@lucide/angular';

import { numberFormatter } from '../../../../../../shared/format';
import type {
  CaseMatches,
  CasePatch,
  ReconciliationCandidate,
  SlaSettings,
  ValidationResult,
} from '../data/models';
import { PendingCasesTableComponent } from './pending-cases-table';
import { ReconciliationQueueComponent } from './reconciliation-queue';
import { ReconciliationTableComponent } from './reconciliation-table';

type TabId = 'cases' | 'closings';

/** O que o separador dos casos mostra: a fila, ou a conciliação em lote dos duplicados. */
type CasesView = 'queue' | 'reconcile';

/** Separadores dos resultados — só um montado de cada vez; por omissão mostra todos os fechos. */
@Component({
  selector: 'app-result-tabs',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    PendingCasesTableComponent,
    ReconciliationQueueComponent,
    ReconciliationTableComponent,
    LucideArrowLeft,
    LucideArrowRight,
    LucideArrowUp,
    LucideLink2,
    LucideTriangleAlert,
  ],
  template: `
    @let r = result();

    <div class="flex flex-col gap-4">
      @if (dataQuality().length > 0) {
        <div
          class="flex items-start gap-2.5 rounded-xl bg-amber-50 px-4 py-3 text-sm ring-1 ring-amber-100"
        >
          <svg
            lucideTriangleAlert
            [size]="16"
            [strokeWidth]="1.9"
            class="mt-0.5 shrink-0 text-amber-600"
          ></svg>
          <div class="flex min-w-0 flex-col gap-0.5">
            <span class="font-semibold text-amber-800">Qualidade dos dados de entrada</span>
            <span class="text-amber-700">{{ dataQuality().join(' · ') }}.</span>
          </div>
        </div>
      }

      <!-- A referência fica no elemento que cola, e não na pastilha lá dentro:
           é a ele que o appPageFirstScroll pergunta quanto falta para assentar. -->
      <div
        #tabList
        class="sticky top-[var(--app-header-h)] z-20 -mx-1 flex items-center gap-3 bg-[#f7f6fb] px-1 py-2"
      >
        <!-- A pista tem de ser mais escura do que a página: é ela que diz «isto
             é um interruptor». A pastilha branca só diz qual está aberta. -->
        <div
          role="tablist"
          aria-label="Vistas do resultado"
          class="inline-flex max-w-full gap-1 overflow-x-auto rounded-xl bg-moza-100 p-1 ring-1 ring-moza-200/70"
        >
          @for (item of tabs(); track item.id) {
            @let active = tab() === item.id;

            <button
              type="button"
              role="tab"
              [attr.aria-selected]="active"
              (click)="tab.set(item.id)"
              class="inline-flex shrink-0 cursor-pointer items-center gap-2 rounded-lg px-3.5 py-2 text-sm font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-moza-400"
              [class]="
                active
                  ? 'bg-white text-moza-800 shadow-sm ring-1 ring-moza-900/5'
                  : 'text-moza-600 hover:bg-white/60 hover:text-moza-800'
              "
            >
              {{ item.label }}
              <span
                class="rounded-full px-1.5 py-0.5 text-2xs font-bold tabular-nums transition-colors"
                [class]="active ? 'bg-moza-100 text-moza-700' : 'bg-moza-200 text-moza-600'"
              >
                {{ item.badge }}
              </span>
            </button>
          }
        </div>

        <!-- Só com os separadores colados, que é o mesmo que dizer «já se está
             na zona das tabelas». «Topo da página» e não «Voltar ao topo»: o
             rodapé da tabela tem um com esse nome que rola a lista, não a página. -->
        @if (stuck()) {
          <button
            type="button"
            (click)="scrollPageToTop()"
            class="ml-auto inline-flex shrink-0 cursor-pointer items-center gap-2 rounded-xl bg-moza-700 px-3.5 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-moza-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-moza-400"
          >
            <svg lucideArrowUp [size]="15" [strokeWidth]="2.2" class="shrink-0"></svg>
            <span class="hidden sm:inline">Topo da página</span>
            <span class="sr-only sm:hidden">Topo da página</span>
          </button>
        }
      </div>

      @if (tab() === 'cases') {
        <!-- A conciliação em lote vive dentro dos casos: são os mesmos casos de
             períodos duplicados, tratados de uma vez. A fila é a vista principal;
             a faixa só aparece quando há o que conciliar, e leva até lá. -->
        @if (showReconcile()) {
          <div class="flex flex-wrap items-center gap-x-3 gap-y-1">
            <button
              type="button"
              (click)="casesView.set('queue')"
              class="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm font-semibold text-gray-600 transition-colors hover:bg-white hover:text-gray-900"
            >
              <svg lucideArrowLeft [size]="15" [strokeWidth]="2.2"></svg>
              Voltar aos casos
            </button>
            <span class="text-sm text-gray-500">
              <b class="font-semibold text-gray-900">Conciliar períodos duplicados</b> — cada fecho
              da SIMO com o crédito do Banka de valor igual.
            </span>
          </div>
          <app-reconciliation-queue
            [executionId]="r.executionId"
            [candidates]="reconciliationCandidates()"
            [settings]="settings()"
            [busy]="reconciling()"
            (reconciledMany)="reconcileCases.emit($event)"
            (updated)="updateCase.emit($event)"
            (reconciled)="reconcileCase.emit($event)"
          />
        } @else {
          @if (reconcilableCount() > 0) {
            <div
              class="flex flex-wrap items-center gap-3 rounded-2xl bg-white px-4 py-3 shadow-sm ring-1 ring-emerald-100"
            >
              <span
                class="inline-flex size-9 shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600"
              >
                <svg lucideLink2 [size]="18" [strokeWidth]="2.2"></svg>
              </span>
              <p class="min-w-0 flex-1 text-sm leading-snug text-gray-600">
                <b class="font-semibold text-gray-900">
                  {{ n(reconcilableCount()) }}
                  {{
                    reconcilableCount() === 1
                      ? 'caso de período duplicado pode ser conciliado'
                      : 'casos de períodos duplicados podem ser conciliados'
                  }}
                  de uma vez.
                </b>
                Cada fecho tem no Banka um crédito de valor igual.
              </p>
              <button
                type="button"
                (click)="casesView.set('reconcile')"
                class="inline-flex shrink-0 items-center gap-1.5 rounded-xl bg-moza-700 px-3.5 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-moza-800"
              >
                Rever e conciliar
                <svg lucideArrowRight [size]="15" [strokeWidth]="2.2"></svg>
              </button>
            </div>
          }
          <app-pending-cases-table
            [cases]="r.cases"
            [executionId]="r.executionId"
            [settings]="settings()"
            [scrollAnchor]="anchor()"
            [reconcilableIds]="reconcilableIds()"
            (updated)="updateCase.emit($event)"
            (reconciled)="reconcileCase.emit($event)"
          />
        }
      } @else {
        <app-reconciliation-table
          [executionId]="r.executionId"
          [settings]="settings()"
          [revision]="revision()"
          [scrollAnchor]="anchor()"
          (updated)="updateCase.emit($event)"
          (reconciled)="reconcileCase.emit($event)"
        />
      }
    </div>
  `,
})
export class ResultTabsComponent {
  readonly result = input.required<ValidationResult>();
  readonly settings = input.required<SlaSettings>();
  /** Sobe a cada conciliação guardada: a tabela de fechos recarrega com os estados novos. */
  readonly revision = input(0);
  /** A página está a gravar uma conciliação em lote. */
  readonly reconciling = input(false);
  /**
   * As chaves a conciliar com crédito igual; `null` enquanto se pedem. Vêm da
   * página, e não do separador, para o número no separador e a tabela serem
   * sempre a mesma lista — e o número aparecer sem abrir o separador.
   */
  readonly reconciliationCandidates = input<readonly ReconciliationCandidate[] | null>(null);
  readonly updateCase = output<CasePatch>();
  readonly reconcileCase = output<CaseMatches>();
  readonly reconcileCases = output<readonly CaseMatches[]>();

  /** Âncora do `appPageFirstScroll`: os separadores, não a tabela, para ficarem à vista. */
  private readonly tabList = viewChild<ElementRef<HTMLElement>>('tabList');
  protected readonly anchor = computed(() => this.tabList()?.nativeElement);

  protected readonly tab = signal<TabId>('closings');
  /**
   * Volta-se à fila ao mudar de separador — a conciliação é um desvio, não um
   * sítio — e também quando deixa de haver o que conciliar.
   */
  protected readonly casesView = linkedSignal<string, CasesView>({
    source: () => {
      const candidates = this.reconciliationCandidates();
      return `${this.tab()}|${candidates !== null && candidates.length === 0}`;
    },
    computation: () => 'queue',
  });

  /** Os casos que a conciliação em lote cobre — a lista de casos marca-os. */
  protected readonly reconcilableIds = computed<ReadonlySet<string>>(
    () => new Set((this.reconciliationCandidates() ?? []).map((candidate) => candidate.case.id)),
  );
  protected readonly reconcilableCount = computed(() => this.reconcilableIds().size);
  /**
   * Conciliado tudo, volta-se à fila sozinho: a lista vazia não tem mais nada
   * para fazer, e os casos regularizados são o que se quer ver a seguir.
   */
  protected readonly showReconcile = computed(() => this.casesView() === 'reconcile');

  /**
   * Os separadores estão colados. Compara-se com o desvio onde assentam e não
   * com zero: abaixo do lg o `top` deles é o da barra do menu.
   */
  protected readonly stuck = signal(false);

  constructor() {
    const measure = () => {
      const el = this.tabList()?.nativeElement;
      if (!el) return;
      const restsAt = parseFloat(getComputedStyle(el).top) || 0;
      this.stuck.set(el.getBoundingClientRect().top <= restsAt + 1);
    };

    window.addEventListener('scroll', measure, { passive: true });
    window.addEventListener('resize', measure, { passive: true });
    inject(DestroyRef).onDestroy(() => {
      window.removeEventListener('scroll', measure);
      window.removeEventListener('resize', measure);
    });
  }

  protected scrollPageToTop(): void {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  protected readonly dataQuality = computed(() => {
    const { keyCollisions, unregisteredPos } = this.result().summary;
    const notes: string[] = [];
    if (unregisteredPos > 0) {
      notes.push(`${this.n(unregisteredPos)} POS sem cadastro na Lista de POS`);
    }
    if (keyCollisions > 0) {
      notes.push(`${this.n(keyCollisions)} chave(s) com períodos que colidem em módulo 1000`);
    }
    return notes;
  });

  protected readonly tabs = computed(() => {
    const summary = this.result().summary;
    return [
      { id: 'closings' as const, label: 'Todos os Fechos', badge: this.n(summary.processed) },
      { id: 'cases' as const, label: 'Casos para Análise', badge: this.n(summary.openCases) },
    ];
  });

  protected n = (value: number) => numberFormatter.format(value);
}
