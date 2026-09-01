import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

import { CollapsibleCardComponent } from '../../../../../shared/ui/collapsible-card';
import { DonutChartComponent, type DonutSlice } from '../../../../../shared/ui/donut-chart';
import type { ClosingSummary } from '../data/models';

/**
 * Fechos por tratar, em anel.
 *
 * O que aqui está é o assunto: quais são os estados que pedem trabalho, com que
 * cor e por que palavras se chamam. O desenho do anel, a legenda e o destaque
 * estão no app-donut-chart, que não sabe nada de fechos.
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
      { name: 'Não creditado', short: 'não creditados', count: s.missingCount, color: '#57617a' },
      {
        name: 'Creditado incorrectamente',
        short: 'creditados a mais ou a menos',
        count: s.mismatchCount,
        color: '#e8342a',
      },
      {
        name: 'Períodos duplicados',
        short: 'em períodos duplicados',
        count: s.duplicatedPeriods,
        color: '#fe9a00',
      },
    ];
  });
}
