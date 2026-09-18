import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';
import { LucideCircleDot } from '@lucide/angular';

import {
  MultiSelectFilterComponent,
  type FilterOption,
} from '../../../../../../shared/ui/multi-select-filter';
import { CASE_STATUSES, CASE_STATUS_DOT, CASE_STATUS_LABEL } from '../data/case-status';
import type { CaseStatus } from '../data/models';

/**
 * Filtro do tratamento em Casos para Análise: em que ponto está o caso e, com
 * isso, de quem se espera acção — ninguém lhe pegou, está connosco, está na
 * SIMO, ou já fechou. Dá para escolher mais do que um («pendentes e em análise
 * interna», que é a fila de quem trabalha cá dentro).
 *
 * «Fase» dizia o género da coisa e não o que ela responde. O tratamento é o
 * vocabulário do resto do módulo — prazo de tratamento, casos por tratar — e é
 * a palavra que liga este filtro ao prazo que corre ao lado.
 */
@Component({
  selector: 'app-case-status-filter',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MultiSelectFilterComponent, LucideCircleDot],
  template: `
    <app-multi-select-filter
      label="Tratamento"
      allLabel="Todos os casos"
      allShortLabel="Todos"
      noneLabel="Nenhum"
      [options]="options()"
      [selected]="selected()"
      (changed)="changed.emit($any($event))"
    >
      <svg lucideCircleDot filterIcon [size]="15" [strokeWidth]="2" class="shrink-0"></svg>
    </app-multi-select-filter>
  `,
})
export class CaseStatusFilterComponent {
  readonly counts = input.required<Record<CaseStatus, number>>();
  readonly selected = input.required<CaseStatus[]>();
  readonly changed = output<CaseStatus[]>();
  /** Os pontos do tratamento que fazem sentido na vista — nos casos em aberto,
   *  sem «Regularizado», que é o fim da linha. */
  readonly statuses = input<readonly CaseStatus[]>(CASE_STATUSES);

  protected readonly options = computed<FilterOption[]>(() =>
    this.statuses().map((status) => ({
      id: status,
      label: CASE_STATUS_LABEL[status],
      dot: CASE_STATUS_DOT[status],
      count: this.counts()[status],
    })),
  );
}
