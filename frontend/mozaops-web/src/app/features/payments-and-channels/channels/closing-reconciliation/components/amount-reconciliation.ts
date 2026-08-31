import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

import {
  formatAmount,
  formatMzn,
  formatSignedAmount,
  numberFormatter,
} from '../../../../../shared/format';
import { CardComponent } from '../../../../../shared/ui/card';
import type { ClosingSummary } from '../data/models';

interface Row {
  readonly key: string;
  readonly label: string;
  readonly count: number;
  readonly simo: number;
  readonly banka: number;
  readonly barClass: string;
  readonly dotClass: string;
}

/** Reconciliação de montantes — não quantos fechos divergem, mas quanto dinheiro está em cada estado. */
@Component({
  selector: 'app-amount-reconciliation',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CardComponent],
  template: `
    <section appCard class="flex flex-col gap-5">
      <div class="flex flex-wrap items-baseline justify-between gap-2">
        <h2 class="text-lg font-bold">Reconciliação de Montantes</h2>
        <p class="text-xs text-gray-400">Apurado na SIMO vs creditado no Banka · MZN</p>
      </div>

      <!-- Largura mínima: divergências são fracções de ponto percentual, senão a barra sai só verde. -->
      <div class="flex h-2.5 w-full gap-px overflow-hidden rounded-full bg-gray-100">
        @for (row of barRows(); track row.key) {
          <span
            [class]="row.barClass + ' first:rounded-l-full last:rounded-r-full'"
            [style.width.%]="widthOf(row)"
            [style.minWidth.rem]="0.5"
            [title]="row.label + ': ' + mzn(row.simo)"
            aria-hidden="true"
          ></span>
        }
      </div>

      <div class="overflow-x-auto">
        <table class="w-full min-w-xl border-collapse text-sm">
          <thead>
            <tr class="border-b border-gray-100 text-gray-400">
              <th scope="col" [class]="th + ' py-2 pr-3 text-left'">Estado</th>
              <th scope="col" [class]="th + ' px-4 py-2 text-right'">Fechos</th>
              <th scope="col" [class]="th + ' px-4 py-2 text-right'">Montante SIMO</th>
              <th scope="col" [class]="th + ' px-4 py-2 text-right'">Montante Banka</th>
              <th scope="col" [class]="th + ' py-2 pl-3 text-right'">Diferença</th>
            </tr>
          </thead>
          <tbody>
            @for (row of rows(); track row.key) {
              @let difference = row.banka - row.simo;

              <tr class="border-b border-gray-100 text-gray-600">
                <td class="py-3 pr-3">
                  <span class="flex items-center gap-2">
                    <span
                      class="size-2 shrink-0 rounded-full"
                      [class]="row.dotClass"
                      aria-hidden="true"
                    ></span>
                    <span class="font-semibold text-gray-900">{{ row.label }}</span>
                  </span>
                </td>
                <td class="px-4 py-3 text-right tabular-nums">{{ count(row.count) }}</td>
                <td class="px-4 py-3 text-right tabular-nums">{{ amount(row.simo) }}</td>
                <td class="px-4 py-3 text-right tabular-nums">
                  {{ row.key === 'missing' ? '—' : amount(row.banka) }}
                </td>
                <td
                  class="py-3 pl-3 text-right tabular-nums"
                  [class.font-semibold]="difference !== 0"
                  [class.text-alert-600]="difference !== 0"
                >
                  {{ difference === 0 ? '—' : signedAmount(difference) }}
                </td>
              </tr>
            }

            <tr class="font-semibold text-gray-900">
              <td class="py-3 pr-3">Total</td>
              <td class="px-4 py-3 text-right tabular-nums">{{ count(summary().processed) }}</td>
              <td class="px-4 py-3 text-right tabular-nums">{{ amount(totalSimo()) }}</td>
              <td class="px-4 py-3 text-right tabular-nums">{{ amount(totalBanka()) }}</td>
              <td class="py-3 pl-3 text-right tabular-nums text-alert-600">
                {{ signedAmount(totalBanka() - totalSimo()) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  `,
})
export class AmountReconciliationComponent {
  readonly summary = input.required<ClosingSummary>();

  protected readonly th = 'text-2xs font-semibold tracking-wider uppercase';

  protected readonly rows = computed<readonly Row[]>(() => {
    const s = this.summary();
    return [
      {
        key: 'match',
        label: 'Crédito confere',
        count: s.matched,
        simo: s.simoAmountMatched,
        banka: s.bankaAmountMatched,
        barClass: 'bg-emerald-500',
        dotClass: 'bg-emerald-500',
      },
      {
        key: 'mismatch',
        label: 'Creditado incorrectamente',
        count: s.mismatchCount,
        simo: s.simoAmountMismatched,
        banka: s.bankaAmountMismatched,
        barClass: 'bg-alert-500',
        dotClass: 'bg-alert-500',
      },
      {
        key: 'missing',
        label: 'Não creditado',
        count: s.missingCount,
        simo: s.simoAmountMissing,
        banka: 0,
        barClass: 'bg-moza-500',
        dotClass: 'bg-moza-500',
      },
      // Banka duplica tal como a SIMO aqui; dar o lado por zero punha esse dinheiro como em falta.
      {
        key: 'duplicated',
        label: 'Períodos duplicados',
        count: s.duplicatedPeriods,
        simo: s.simoAmountDuplicated,
        banka: s.bankaAmountDuplicated,
        barClass: 'bg-amber-500',
        dotClass: 'bg-amber-500',
      },
    ];
  });

  protected readonly barRows = computed(() => this.rows().filter((row) => row.simo > 0));
  protected readonly totalSimo = computed(() =>
    this.rows().reduce((total, row) => total + row.simo, 0),
  );
  protected readonly totalBanka = computed(() =>
    this.rows().reduce((total, row) => total + row.banka, 0),
  );

  protected widthOf(row: Row): number {
    const total = this.totalSimo();
    return total > 0 ? (row.simo / total) * 100 : 0;
  }

  protected mzn = formatMzn;
  protected amount = formatAmount;
  protected signedAmount = formatSignedAmount;
  protected count = (value: number) => numberFormatter.format(value);
}
