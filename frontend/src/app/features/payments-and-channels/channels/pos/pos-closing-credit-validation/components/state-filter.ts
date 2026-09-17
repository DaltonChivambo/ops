import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';
import { LucideListFilter } from '@lucide/angular';

import {
  MultiSelectFilterComponent,
  type FilterOption,
} from '../../../../../../shared/ui/multi-select-filter';
import type { DetailCounts } from '../data/models';
import { STATE_OPTIONS, type StateId } from '../data/state-options';

/** Filtro da «Validação» em Todos os Fechos — as opções de `STATE_OPTIONS` no filtro partilhado. */
@Component({
  selector: 'app-state-filter',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MultiSelectFilterComponent, LucideListFilter],
  template: `
    <app-multi-select-filter
      label="Validação"
      allLabel="Todas as validações"
      [options]="options()"
      [selected]="selected()"
      (changed)="changed.emit($any($event))"
    >
      <svg lucideListFilter filterIcon [size]="15" [strokeWidth]="2" class="shrink-0"></svg>
    </app-multi-select-filter>
  `,
})
export class StateFilterComponent {
  readonly counts = input.required<DetailCounts>();
  readonly selected = input.required<StateId[]>();
  readonly changed = output<StateId[]>();

  protected readonly options = computed<FilterOption[]>(() =>
    STATE_OPTIONS.map((option) => ({
      id: option.id,
      label: option.label,
      dot: option.dot,
      count: option.count(this.counts()),
    })),
  );
}
