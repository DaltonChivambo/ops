import { ChangeDetectionStrategy, Component, computed, input, signal } from '@angular/core';

import {
  formatAmount,
  formatMzn,
  formatSignedAmount,
  numberFormatter,
  percentageShares,
} from '../../../../../shared/format';
import { CollapsibleCardComponent } from '../../../../../shared/ui/collapsible-card';
import { StackedBarComponent, type BarSegment } from '../../../../../shared/ui/stacked-bar';
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
  imports: [CollapsibleCardComponent, StackedBarComponent],
  template: `
    <app-collapsible-card heading="Reconciliação de Montantes" storageKey="reconciliacao-montantes">
      <p cardAside class="text-xs text-gray-400">Apurado na SIMO vs creditado no Banka · MZN</p>

      <div class="flex flex-col gap-2">
        <app-stacked-bar [segments]="barSegments()" [(active)]="active" />

        <!-- Reserva a altura sempre, para a barra não saltar quando isto aparece. -->
        <p class="flex min-h-4 items-center gap-2 text-xs">
          @if (activeRow(); as row) {
            <span class="size-2 shrink-0 rounded-full" [class]="row.dotClass"></span>
            <span class="font-semibold text-gray-900">{{ row.label }}</span>
            <span class="text-gray-400">{{ share(row) }} do apurado na SIMO</span>
            <span class="ml-auto font-semibold whitespace-nowrap tabular-nums text-gray-900">
              {{ amount(row.simo) }} <span class="font-normal text-gray-400">MZN</span>
            </span>
          }
        </p>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full min-w-xl border-collapse text-sm">
          <thead>
            <tr class="border-b border-gray-100 text-gray-400">
              <th scope="col" [class]="th + ' py-2 pr-3 pl-1.5 text-left'">Estado</th>
              <th scope="col" [class]="th + ' px-4 py-2 text-right'">Fechos</th>
              <th scope="col" [class]="th + ' px-4 py-2 text-right'">Montante SIMO</th>
              <th scope="col" [class]="th + ' px-4 py-2 text-right'">Montante Banka</th>
              <th scope="col" [class]="th + ' py-2 pr-1.5 pl-3 text-right'">Diferença</th>
            </tr>
          </thead>
          <tbody>
            @for (row of rows(); track row.key) {
              @let difference = row.banka - row.simo;
              @let on = active() === row.key;

              <tr
                class="border-b border-gray-100 text-gray-600 transition-colors"
                [class.bg-gray-50]="on"
                (mouseenter)="active.set(row.key)"
                (mouseleave)="active.set(null)"
              >
                <td class="py-3 pr-3 pl-1.5">
                  <span class="flex items-center gap-2">
                    <span
                      class="size-2 shrink-0 rounded-full transition-transform"
                      [class]="row.dotClass"
                      [class.scale-125]="on"
                      aria-hidden="true"
                    ></span>
                    <span class="font-semibold text-gray-900">{{ row.label }}</span>
                  </span>
                </td>
                <td class="px-4 py-3 text-right whitespace-nowrap tabular-nums">
                  {{ count(row.count) }}
                </td>
                <td class="px-4 py-3 text-right whitespace-nowrap tabular-nums">
                  {{ amount(row.simo) }}
                </td>
                <td class="px-4 py-3 text-right whitespace-nowrap tabular-nums">
                  {{ row.key === 'missing' ? '—' : amount(row.banka) }}
                </td>
                <td
                  class="py-3 pr-1.5 pl-3 text-right whitespace-nowrap tabular-nums"
                  [class.font-semibold]="difference !== 0"
                  [class.text-alert-600]="difference !== 0"
                >
                  {{ difference === 0 ? '—' : signedAmount(difference) }}
                </td>
              </tr>
            }

            <tr class="font-semibold text-gray-900">
              <td class="py-3 pr-3 pl-1.5">Total</td>
              <td class="px-4 py-3 text-right whitespace-nowrap tabular-nums">
                {{ count(summary().processed) }}
              </td>
              <td class="px-4 py-3 text-right whitespace-nowrap tabular-nums">
                {{ amount(totalSimo()) }}
              </td>
              <td class="px-4 py-3 text-right whitespace-nowrap tabular-nums">
                {{ amount(totalBanka()) }}
              </td>
              <td class="py-3 pr-1.5 pl-3 text-right whitespace-nowrap tabular-nums text-alert-600">
                {{ signedAmount(totalBanka() - totalSimo()) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </app-collapsible-card>
  `,
})
export class AmountReconciliationComponent {
  readonly summary = input.required<ClosingSummary>();

  protected readonly th = 'text-2xs font-semibold tracking-wider uppercase';

  /** Estado em destaque — vindo da barra ou da linha da tabela, indiferentemente. */
  protected readonly active = signal<string | null>(null);

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

  /**
   * Os segmentos para a barra. O rótulo acessível é montado aqui e não no
   * gráfico: é deste lado que se sabe que os valores são meticais e que a quota
   * é sobre o apurado na SIMO.
   */
  protected readonly barSegments = computed<readonly BarSegment[]>(() =>
    this.rows()
      .filter((row) => row.simo > 0)
      .map((row) => ({
        key: row.key,
        label: row.label,
        value: row.simo,
        className: row.barClass,
        ariaLabel: `${row.label}: ${this.mzn(row.simo)}, ${this.share(row)}`,
      })),
  );

  protected readonly activeRow = computed(
    () => this.rows().find((row) => row.key === this.active()) ?? null,
  );
  protected readonly totalSimo = computed(() =>
    this.rows().reduce((total, row) => total + row.simo, 0),
  );
  protected readonly totalBanka = computed(() =>
    this.rows().reduce((total, row) => total + row.banka, 0),
  );

  /**
   * Quota de cada estado no total apurado na SIMO — o que a barra desenha.
   *
   * Calculadas todas de uma vez, e não uma a uma: arredondadas isoladamente não
   * fechariam 100%. Aqui só se mostra uma de cada vez, na legenda por baixo da
   * barra, mas quem soma os quatro segmentos com os olhos tem de chegar ao todo.
   */
  private readonly sharesByKey = computed(() => {
    const rows = this.rows();
    const shares = percentageShares(rows.map((row) => row.simo));
    return new Map(rows.map((row, index) => [row.key, shares[index]]));
  });

  protected share(row: Row): string {
    return this.sharesByKey().get(row.key) ?? '0%';
  }

  protected widthOf(row: Row): number {
    const total = this.totalSimo();
    return total > 0 ? (row.simo / total) * 100 : 0;
  }

  protected mzn = formatMzn;
  protected amount = formatAmount;
  protected signedAmount = formatSignedAmount;
  protected count = (value: number) => numberFormatter.format(value);
}
