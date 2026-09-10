import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

import { CollapsibleCardComponent } from '../../../../../../shared/ui/collapsible-card';
import { DonutChartComponent, type DonutSlice } from '../../../../../../shared/ui/donut-chart';
import type { ClosingSummary } from '../data/models';

/**
 * Fechos por tratar, em anel — o desenho está no app-donut-chart.
 *
 * Os duplicados entram apesar de não serem divergência: ninguém sabe se a chave
 * confere enquanto a duplicação não se desfizer, e é trabalho igual.
 */
@Component({
  selector: 'app-discrepancy-source-donut',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CollapsibleCardComponent, DonutChartComponent],
  template: `
    <app-collapsible-card heading="Fechos por Tratar" storageKey="fechos-por-tratar">
      <app-donut-chart
        [slices]="slices()"
        caption="por tratar"
        emptyMessage="Todos os fechos conferem."
        ariaPrefix="Fechos por tratar"
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
        description: 'Apurado na SIMO, mas sem crédito correspondente no Banka.',
      },
      {
        name: 'Creditado incorrectamente',
        short: 'incorrectamente creditados',
        count: s.mismatchCount,
        color: '#e8342a',
        description: 'Foi creditado no Banka, mas o valor não corresponde ao apurado na SIMO.',
      },
      {
        name: 'Períodos duplicados',
        short: 'em períodos duplicados',
        count: s.duplicatedPeriods,
        color: '#fe9a00',
        description: 'Um POS tem mais de um fecho para o mesmo período — a chave é POS + período.',
      },
    ];
  });
}
