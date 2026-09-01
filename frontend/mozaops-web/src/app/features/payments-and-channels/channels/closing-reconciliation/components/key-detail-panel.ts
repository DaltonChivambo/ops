import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  computed,
  effect,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { LucideLoaderCircle, LucideX } from '@lucide/angular';

import { formatAmount, formatDate, formatSignedAmount, numberFormatter } from '../../../../../shared/format';
import { ReconciliationApi } from '../data/reconciliation-api.service';
import { STATE_CHIP, STATE_DOT, STATE_LABEL } from '../data/state-options';
import type { ClosingDetail, KeyBreakdown } from '../data/models';

const CASE_STATUS_LABEL: Record<string, string> = {
  pending: 'Pendente',
  'in-review': 'Em análise',
  resolved: 'Regularizado',
};

/**
 * "3 dias depois" / "no mesmo dia" — o sentido vai no valor, não no cabeçalho.
 * `null` numa chave com vários fechos: não se sabe qual crédito é de qual.
 */
function creditedWhen(closingIso: string | undefined, creditIso: string | null): string | null {
  if (!closingIso || !creditIso) return null;
  const day = 24 * 60 * 60 * 1000;
  const closing = new Date(`${closingIso.slice(0, 10)}T00:00:00`).getTime();
  const credit = new Date(`${creditIso.slice(0, 10)}T00:00:00`).getTime();
  const days = Math.round((credit - closing) / day);
  if (days === 0) return 'no mesmo dia';
  const span = `${Math.abs(days)} ${Math.abs(days) === 1 ? 'dia' : 'dias'}`;
  return `${span} ${days > 0 ? 'depois' : 'antes'}`;
}

/**
 * Painel lateral com os dois lados de uma chave — fechos SIMO e movimentos Banka.
 * A unidade é a CHAVE e não o fecho: o crédito do Banka é da chave, um fecho
 * isolado não tem crédito próprio.
 */
@Component({
  selector: 'app-key-detail-panel',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [LucideLoaderCircle, LucideX],
  host: {
    '(document:keydown.escape)': 'closed.emit()',
  },
  template: `
    @let d = detail();

    <div class="fixed inset-0 z-40 bg-gray-900/20" aria-hidden="true" (click)="closed.emit()"></div>

    <aside
      role="dialog"
      aria-modal="true"
      [attr.aria-label]="'Fecho do POS ' + d.posId + ', período ' + d.period"
      class="fixed inset-y-0 right-0 z-50 flex w-full max-w-2xl flex-col bg-white shadow-2xl"
    >
      <header class="flex items-start gap-3 border-b border-gray-100 px-5 py-4">
        <div class="min-w-0 flex-1">
          <div class="flex flex-wrap items-center gap-2">
            <h2 class="text-lg font-bold text-gray-900 tabular-nums">POS {{ d.posId }}</h2>
            <span
              class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-bold whitespace-nowrap"
              [class]="chip()"
            >
              <span class="size-1.5 rounded-full" [class]="dot()"></span>
              {{ stateLabel() }}
            </span>
          </div>

          <p class="mt-0.5 truncate text-sm text-gray-500">{{ d.merchant }}</p>

          <div class="mt-2 flex flex-wrap items-baseline gap-x-4 gap-y-1 text-xs">
            <span [class]="meta">
              <span class="text-gray-400">Conta</span>
              <span [class]="metaValue">{{ d.accountNumber }}</span>
            </span>
            <span [class]="meta">
              <span class="text-gray-400">Período</span>
              <span [class]="metaValue">{{ d.period }}</span>
            </span>
            <span [class]="meta">
              <span class="text-gray-400">Fecho</span>
              <span [class]="metaValue">{{ d.closingType }}</span>
            </span>
            <span [class]="meta">
              <span class="text-gray-400">Chave</span>
              <span [class]="metaValue">{{ d.key }}</span>
            </span>
          </div>
        </div>

        <button
          type="button"
          (click)="closed.emit()"
          aria-label="Fechar"
          class="inline-flex size-8 shrink-0 items-center justify-center rounded-lg text-gray-400 transition-colors hover:bg-gray-50 hover:text-gray-900"
        >
          <svg lucideX [size]="18" [strokeWidth]="2.2"></svg>
        </button>
      </header>

      <div class="flex-1 overflow-y-auto px-5 py-5">
        @if (error(); as message) {
          <p class="rounded-xl bg-alert-50 px-4 py-3 text-sm text-alert-700">{{ message }}</p>
        }

        @if (!data() && !error()) {
          <p class="mt-8 flex items-center justify-center gap-2 text-sm text-gray-400">
            <svg lucideLoaderCircle [size]="15" [strokeWidth]="2" class="animate-spin"></svg>
            A abrir o fecho…
          </p>
        }

        @if (data(); as breakdown) {
          <!-- Apuramento à cabeça, é a conclusão; as listas por baixo são a demonstração.
               Empilha abaixo do sm: o painel ocupa a largura toda num ecrã
               estreito, e três montantes lado a lado ficam ilegíveis. -->
          <section
            class="grid grid-cols-1 gap-4 rounded-xl border border-gray-100 px-4 py-3.5 sm:grid-cols-3"
          >
            <div class="min-w-0">
              <p [class]="totalLabel">Apurado na SIMO</p>
              <p [class]="totalValue + ' text-gray-900'">
                {{ amount(simoTotal()) }}<span [class]="mzn">MZN</span>
              </p>
            </div>
            <div class="min-w-0">
              <p [class]="totalLabel">Creditado no Banka</p>
              <p [class]="totalValue + ' text-gray-900'">
                {{ amount(bankaTotal()) }}<span [class]="mzn">MZN</span>
              </p>
            </div>
            <div class="min-w-0">
              <p [class]="totalLabel">Diferença</p>
              <p
                [class]="totalValue"
                [class.text-emerald-600]="difference() === 0"
                [class.text-alert-600]="difference() !== 0"
              >
                {{ signed(difference()) }}<span [class]="mzn">MZN</span>
              </p>
            </div>
          </section>

          <!-- Fundo neutro: os dois lados levam tons diferentes, não cores — não há bom/mau aqui. -->
          <section class="mt-4 rounded-xl bg-gray-50/80 px-4 py-3.5 ring-1 ring-gray-100">
            <h3 [class]="sectionTitle">
              Portal SIMO ·
              {{
                closings().length === 1
                  ? 'o fecho apurado'
                  : n(closings().length) + ' fechos apurados'
              }}
            </h3>

            <!-- Scroll próprio em vez de espremer as colunas: o painel ocupa a
                 largura toda num ecrã estreito, e um montante partido não se lê. -->
            <div class="mt-2.5 overflow-x-auto">
            <table class="w-full min-w-sm border-collapse text-sm">
              <thead>
                <tr class="border-b border-gray-100 text-gray-400">
                  <th scope="col" [class]="th + ' py-2 pr-3 text-left'">Data Fecho</th>
                  <th scope="col" [class]="th + ' px-3 py-2 text-right'">Nº Operaç.</th>
                  <th scope="col" [class]="th + ' py-2 pl-3 text-right'">Total do fecho</th>
                </tr>
              </thead>
              <tbody>
                @for (closing of closings(); track closing.id) {
                  <!-- O fecho clicado assinala-se pelo fundo branco, sem marca à frente da data. -->
                  <tr
                    class="border-b border-gray-100/80 last:border-b-0"
                    [class]="closing.id === d.id ? 'bg-white text-gray-900' : 'text-gray-600'"
                  >
                    <td class="py-2.5 pr-3 tabular-nums">{{ date(closing.simoClosingDate) }}</td>
                    <td class="px-3 py-2.5 text-right tabular-nums text-gray-400">
                      {{ closing.operationNumber }}
                    </td>
                    <td class="py-2.5 pl-3 text-right">
                      <span class="font-semibold whitespace-nowrap tabular-nums text-gray-900">
                        {{ amount(closing.simoClosingTotal) }}<span [class]="mzn">MZN</span>
                      </span>
                    </td>
                  </tr>
                }
              </tbody>
              <!-- A soma vive no pé da coluna que soma, alinhada para se conferir a conta. -->
              <tfoot>
                <tr class="border-t border-gray-200">
                  <td class="pt-2.5 pr-3 text-xs text-gray-500" colspan="2">
                    Total apurado
                  </td>
                  <td class="pt-2.5 pl-3 text-right">
                    <span class="font-semibold whitespace-nowrap tabular-nums text-gray-900">
                      {{ amount(simoTotal()) }}<span [class]="mzn">MZN</span>
                    </span>
                  </td>
                </tr>
              </tfoot>
            </table>
            </div>
          </section>

          <section class="mt-4 rounded-xl bg-moza-50 px-4 py-3.5 ring-1 ring-moza-200">
            <h3 [class]="sectionTitle">
              Banka ·
              {{
                movements().length === 0
                  ? 'sem crédito'
                  : n(movements().length) +
                    ' ' +
                    (movements().length === 1 ? 'movimento creditado' : 'movimentos creditados')
              }}
            </h3>

            @if (sharedDescription(); as shared) {
              <p class="mt-1 truncate text-xs text-gray-400">{{ shared }}</p>
            }

            @if (movements().length === 0) {
              <p class="mt-2.5 rounded-xl bg-white/70 px-4 py-3 text-sm text-gray-500">
                Não há nenhum movimento do Banka com esta chave.
                @if (d.bankaClosingTotal !== null) {
                  O crédito da chave está apurado em
                  <b class="text-gray-900">{{ amount(d.bankaClosingTotal) }} MZN</b>, mas as parcelas
                  não foram guardadas — é uma execução anterior à versão que as passou a registar.
                  Volte a correr a validação para as ver.
                }
              </p>
            } @else {
              <div class="mt-2.5 overflow-x-auto">
              <table class="w-full min-w-md border-collapse text-sm">
                <thead>
                  <tr class="border-b border-moza-200 text-gray-400">
                    <th scope="col" [class]="th + ' py-2 pr-3 text-left'">Data Crédito</th>
                    <th scope="col" [class]="th + ' px-3 py-2 text-left'">Creditado</th>
                    @if (!sharedDescription()) {
                      <th scope="col" [class]="th + ' px-3 py-2 text-left'">Descritivo</th>
                    }
                    <th scope="col" [class]="th + ' py-2 pl-3 text-right'">Valor</th>
                  </tr>
                </thead>
                <tbody>
                  @for (movement of movements(); track movement.id) {
                    <tr class="border-b border-moza-100 text-gray-600 last:border-b-0">
                      <td class="py-2.5 pr-3 tabular-nums">
                        {{ movement.date ? date(movement.date) : '—' }}
                      </td>
                      <td class="px-3 py-2.5 whitespace-nowrap">
                        @if (whenCredited(movement.date); as when) {
                          {{ when }}
                        } @else {
                          <span class="text-gray-300">—</span>
                        }
                      </td>
                      @if (!sharedDescription()) {
                        <td class="px-3 py-2.5">
                          <span class="block max-w-64 truncate text-sm">
                            {{ movement.description || '—' }}
                          </span>
                        </td>
                      }
                      <td class="py-2.5 pl-3 text-right">
                        <span class="font-semibold whitespace-nowrap tabular-nums text-gray-900">
                          {{ amount(movement.amount) }}<span [class]="mzn">MZN</span>
                        </span>
                      </td>
                    </tr>
                  }
                </tbody>
                <tfoot>
                  <tr class="border-t border-moza-200">
                    <td
                      class="pt-2.5 pr-3 text-xs text-gray-500"
                      [attr.colspan]="sharedDescription() ? 2 : 3"
                    >
                      Total creditado
                    </td>
                    <td class="pt-2.5 pl-3 text-right">
                      <span class="font-semibold whitespace-nowrap tabular-nums text-gray-900">
                        {{ amount(bankaTotal()) }}<span [class]="mzn">MZN</span>
                      </span>
                    </td>
                  </tr>
                </tfoot>
              </table>
              </div>
            }
          </section>

          @if (breakdown.case; as pendingCase) {
            <section class="mt-4 rounded-xl border border-gray-100 px-4 py-3.5">
              <h3 [class]="sectionTitle">Caso pendente na SIMO</h3>
              <dl class="mt-2.5 grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-3">
                <div class="min-w-0">
                  <dt [class]="fieldLabel">Estado</dt>
                  <dd [class]="fieldValue">{{ caseStatus(pendingCase.status) }}</dd>
                </div>
                <div class="min-w-0">
                  <dt [class]="fieldLabel">e-Ticket</dt>
                  <dd [class]="fieldValue">{{ pendingCase.eTicket || '—' }}</dd>
                </div>
                <div class="min-w-0">
                  <dt [class]="fieldLabel">Data Reg.</dt>
                  <dd [class]="fieldValue">
                    {{ pendingCase.resolvedAt ? date(pendingCase.resolvedAt) : '—' }}
                  </dd>
                </div>
              </dl>
            </section>
          }
        }
      </div>
    </aside>
  `,
})
export class KeyDetailPanelComponent {
  private readonly api = inject(ReconciliationApi);

  readonly executionId = input.required<string>();
  /** O fecho clicado — dá a identidade e fica assinalado na lista da SIMO. */
  readonly detail = input.required<ClosingDetail>();
  readonly closed = output<void>();

  protected readonly data = signal<KeyBreakdown | null>(null);
  protected readonly error = signal<string | null>(null);

  protected readonly meta = 'inline-flex items-baseline gap-1.5 whitespace-nowrap';
  protected readonly metaValue = 'font-semibold text-gray-700 tabular-nums';
  protected readonly mzn = 'ml-1 text-[0.7em] font-normal text-gray-400';
  protected readonly th = 'text-2xs font-bold tracking-wider uppercase';
  protected readonly sectionTitle =
    'text-2xs font-bold tracking-wider text-gray-400 uppercase';
  protected readonly totalLabel =
    'text-2xs font-bold tracking-wider text-gray-400 uppercase';
  protected readonly totalValue = 'mt-1 text-base font-bold tabular-nums';
  protected readonly fieldLabel =
    'text-2xs font-bold tracking-wider text-gray-400 uppercase';
  protected readonly fieldValue =
    'mt-0.5 truncate text-sm font-semibold text-gray-900';

  protected readonly closings = computed(() => this.data()?.closings ?? []);
  protected readonly movements = computed(() => this.data()?.movements ?? []);
  protected readonly simoTotal = computed(() => this.detail().simoKeyTotal);

  /**
   * Sem parcelas guardadas (execução anterior à migração) cai-se no total já
   * apurado da chave: o apuramento continua certo, só não há detalhe para somar.
   */
  protected readonly bankaTotal = computed(() => {
    const movements = this.movements();
    if (movements.length > 0) {
      return movements.reduce((total, movement) => total + movement.amount, 0);
    }
    return this.detail().bankaClosingTotal ?? 0;
  });

  protected readonly difference = computed(() => this.bankaTotal() - this.simoTotal());

  /** Igual em todos os movimentos: mostra-se uma vez no topo e a coluna desaparece. */
  protected readonly sharedDescription = computed(() => {
    const descriptions = new Set(this.movements().map((movement) => movement.description ?? ''));
    return descriptions.size === 1 ? ([...descriptions][0] || null) : null;
  });

  /** Só se pode datar o prazo com um único fecho na chave — com vários, não se sabe qual é qual. */
  private readonly soleClosingDate = computed(() => {
    const closings = this.closings();
    return closings.length === 1 ? closings[0].simoClosingDate : undefined;
  });

  protected readonly chip = computed(() => STATE_CHIP[this.detail().validation]);
  protected readonly dot = computed(() => STATE_DOT[this.detail().validation]);
  protected readonly stateLabel = computed(() => STATE_LABEL[this.detail().validation]);

  constructor() {
    // Recarrega a cada chave: abrir outro fecho reutiliza o painel já montado.
    effect((onCleanup) => {
      const executionId = this.executionId();
      const key = this.detail().key;

      let cancelled = false;
      onCleanup(() => {
        cancelled = true;
      });

      this.data.set(null);
      this.error.set(null);

      void this.api
        .getKeyBreakdown(executionId, key)
        .then((result) => {
          if (!cancelled) this.data.set(result);
        })
        .catch((problem: unknown) => {
          if (cancelled) return;
          this.error.set(
            problem instanceof Error ? problem.message : 'Não foi possível abrir o fecho.',
          );
        });
    });

    // Tranca o scroll da página (compensando a largura da barra em padding, para
    // o conteúdo não saltar) enquanto o painel está aberto.
    const { body } = document;
    const scrollbar = window.innerWidth - document.documentElement.clientWidth;
    const previous = { overflow: body.style.overflow, paddingRight: body.style.paddingRight };
    body.style.overflow = 'hidden';
    if (scrollbar > 0) body.style.paddingRight = `${scrollbar}px`;

    inject(DestroyRef).onDestroy(() => {
      body.style.overflow = previous.overflow;
      body.style.paddingRight = previous.paddingRight;
    });
  }

  protected whenCredited(creditIso: string | null): string | null {
    return creditedWhen(this.soleClosingDate(), creditIso);
  }

  protected caseStatus = (status: string) => CASE_STATUS_LABEL[status] ?? status;
  protected amount = formatAmount;
  protected signed = formatSignedAmount;
  protected date = formatDate;
  protected n = (value: number) => numberFormatter.format(value);
}
