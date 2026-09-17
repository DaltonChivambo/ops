import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';
import { LucideCircleDot } from '@lucide/angular';

import {
  MultiSelectFilterComponent,
  type FilterOption,
} from '../../../../../../shared/ui/multi-select-filter';
import { CASE_STATUSES, CASE_STATUS_DOT, CASE_STATUS_LABEL } from '../data/case-status';
import type { CaseStatus } from '../data/models';

/**
 * Filtro da «Fase» do tratamento em Casos para Análise — dá para escolher mais
 * de uma («pendentes e em análise interna»).
 */
@Component({
  selector: 'app-case-status-filter',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MultiSelectFilterComponent, LucideCircleDot],
  template: `
    <app-multi-select-filter
      label="Fase"
      allLabel="Todas as fases"
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
  /** As fases que fazem sentido na vista — nos casos em aberto, sem «Regularizado». */
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
