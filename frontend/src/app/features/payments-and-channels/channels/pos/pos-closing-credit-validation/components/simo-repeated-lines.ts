import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';
import { LucideCopyCheck, LucideCopyX, LucideLoaderCircle } from '@lucide/angular';

import { formatAmount, numberFormatter } from '../../../../../../shared/format';
import { InfoTooltipComponent } from '../../../../../../shared/ui/info-tooltip';
import type { ClosingSummary } from '../data/models';

/**
 * A faixa dos fechos repetidos da SIMO, e a decisão sobre eles.
 *
 * O mesmo fecho aparece às vezes mais do que uma vez na SIMO, igual em tudo.
 * **Não é um fecho novo**: o estado da chave é o do fecho original e não se
 * mexe — continua em «Confere», ou no que for. O que fica por decidir é só o
 * dinheiro: se o montante deles entra na reconciliação ou fica de fora.
 *
 * Fica por cima do cartão dos montantes e não dentro dele: é uma decisão sobre a
 * execução, e o cartão é onde ela se vê.
 */
@Component({
  selector: 'app-simo-repeated-lines',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [InfoTooltipComponent, LucideCopyCheck, LucideCopyX, LucideLoaderCircle],
  template: `
    @if (rows() > 0) {
      <div
        class="flex flex-wrap items-center gap-x-3 gap-y-2 rounded-xl px-3 py-2.5 ring-1"
        [class]="counted() ? 'bg-amber-50 ring-amber-200' : 'bg-white ring-gray-100'"
      >
        <p class="text-xs text-gray-500">
          <b class="font-semibold text-gray-900 tabular-nums">{{ count(rows()) }}</b>
          {{ rows() === 1 ? 'fecho repetido' : 'fechos repetidos' }} na SIMO ·
          <b class="font-semibold text-gray-900 tabular-nums">{{ amount(total()) }}</b> MZN
          <span class="font-semibold" [class]="counted() ? 'text-amber-700' : 'text-gray-400'">
            {{ counted() ? 'no apuramento' : 'fora do apuramento' }}
          </span>
          @if (uncovered() > 0) {
            <span class="text-gray-400">
              · <b class="font-semibold text-alert-600 tabular-nums">{{ amount(uncovered()) }}</b>
              sem crédito no Banka
            </span>
          }
        </p>

        <app-info-tooltip [text]="explanation()" label="Sobre os fechos repetidos da SIMO" />

        <button
          type="button"
          (click)="countedChanged.emit(!counted())"
          [disabled]="busy()"
          class="ml-auto inline-flex shrink-0 items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-bold whitespace-nowrap shadow-sm transition-colors disabled:cursor-not-allowed disabled:bg-gray-200 disabled:text-gray-400 disabled:shadow-none"
          [class]="
            counted()
              ? 'bg-white text-amber-800 hover:bg-amber-100'
              : 'bg-moza-700 text-white hover:bg-moza-800'
          "
        >
          @if (busy()) {
            <svg lucideLoaderCircle [size]="14" [strokeWidth]="2.2" class="animate-spin"></svg>
            A guardar…
          } @else if (counted()) {
            <svg lucideCopyX [size]="14" [strokeWidth]="2.2"></svg>
            Não considerar
          } @else {
            <svg lucideCopyCheck [size]="14" [strokeWidth]="2.2"></svg>
            Considerar
          }
        </button>
      </div>
    }
  `,
})
export class SimoRepeatedLinesComponent {
  readonly summary = input.required<ClosingSummary>();
  /** A gravação da decisão está a correr — o botão fica preso até voltar. */
  readonly busy = input(false);
  /** O operador mandou contar, ou não, o dinheiro destas linhas. */
  readonly countedChanged = output<boolean>();

  protected readonly rows = computed(() => this.summary().duplicatesDiscarded);
  protected readonly total = computed(() => this.summary().simoAmountDuplicateRows ?? 0);
  /** O crédito do Banka que lhes corresponde — o que pagou o fecho original. */
  protected readonly covered = computed(() => this.summary().bankaAmountDuplicateRows ?? 0);
  /** O que fica sem correspondência: chaves que o Banka não creditou. */
  protected readonly uncovered = computed(() => Math.max(this.total() - this.covered(), 0));
  protected readonly counted = computed(() => this.summary().countSimoDuplicates === true);

  protected readonly explanation = computed(() =>
    this.counted()
      ? 'O mesmo fecho aparece mais do que uma vez na SIMO, igual em POS, período, data, nº de operações e total. Entram nos dois lados, com o crédito que pagou o fecho original. O estado da chave não muda.'
      : 'O mesmo fecho aparece mais do que uma vez na SIMO, igual em POS, período, data, nº de operações e total. Não é um fecho novo: o dinheiro conta uma vez e o estado é o do fecho original.',
  );

  protected amount = (value: number) => formatAmount(value);
  protected count = (value: number) => numberFormatter.format(value);
}
