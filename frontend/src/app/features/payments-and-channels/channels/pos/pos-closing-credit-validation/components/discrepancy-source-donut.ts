import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

import { CollapsibleCardComponent } from '../../../../../../shared/ui/collapsible-card';
import { DonutChartComponent, type DonutSlice } from '../../../../../../shared/ui/donut-chart';
import type { ClosingSummary } from '../data/models';

/**
 * O que está por tratar, em anel — o desenho está no app-donut-chart.
 *
 * Os repetidos entram apesar de não serem divergência: ninguém sabe se a chave
 * confere enquanto a duplicação não se desfizer, e é trabalho igual.
 */
@Component({
  selector: 'app-discrepancy-source-donut',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CollapsibleCardComponent, DonutChartComponent],
  template: `
    <app-collapsible-card heading="Por Tratar" storageKey="fechos-por-tratar">
      <app-donut-chart
        [slices]="slices()"
        caption="por tratar"
        emptyMessage="Todos os fechos conferem."
        ariaPrefix="Por tratar"
      />
    </app-collapsible-card>
  `,
})
export class DiscrepancySourceDonutComponent {
  readonly summary = input.required<ClosingSummary>();

  protected readonly slices = computed<readonly DonutSlice[]>(() => {
    const s = this.summary();
    return [
      {
        name: 'Não creditado',
        short: 'não creditados',
        count: s.missingCount,
        color: '#57617a',
        description: 'Fechos apurados na SIMO, mas sem crédito correspondente no Banka.',
      },
      {
        name: 'Creditado incorrectamente',
        short: 'incorrectamente creditados',
        count: s.mismatchCount,
        color: '#e8342a',
        description: 'Fechos creditados no Banka, mas com valor diferente do apurado na SIMO.',
      },
      {
        name: 'Períodos repetidos',
        short: 'em períodos repetidos',
        count: s.duplicatedPeriods,
        color: '#fe9a00',
        description:
          'Fechos com períodos repetidos: o mesmo POS e período aparece mais do que uma vez, na SIMO ou no Banka.',
      },
    ];
  });
}
