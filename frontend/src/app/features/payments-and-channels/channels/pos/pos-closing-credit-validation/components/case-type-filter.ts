import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';
import { LucideListFilter } from '@lucide/angular';

import {
  MultiSelectFilterComponent,
  type FilterOption,
} from '../../../../../../shared/ui/multi-select-filter';
import type { CaseType } from '../data/models';

/** Mesma prioridade usada em todo o ecrã: incorrecto, não creditado, repetido. */
const TYPES: ReadonlyArray<{ id: CaseType; label: string; dot: string }> = [
  { id: 'mismatch', label: 'Incorrecto', dot: 'bg-alert-500' },
  { id: 'missing', label: 'Não creditado', dot: 'bg-moza-500' },
  { id: 'duplicated', label: 'Período repetido', dot: 'bg-amber-500' },
];

/** Filtro da «Divergência» em Casos para Análise — os três tipos de caso no filtro partilhado. */
@Component({
  selector: 'app-case-type-filter',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MultiSelectFilterComponent, LucideListFilter],
  template: `
    <app-multi-select-filter
      label="Divergência"
      allLabel="Todas as divergências"
      [options]="options()"
      [selected]="selected()"
      (changed)="changed.emit($any($event))"
    >
      <svg lucideListFilter filterIcon [size]="15" [strokeWidth]="2" class="shrink-0"></svg>
    </app-multi-select-filter>
  `,
})
export class CaseTypeFilterComponent {
  readonly counts = input.required<Record<CaseType, number>>();
  readonly selected = input.required<CaseType[]>();
  readonly changed = output<CaseType[]>();

  protected readonly options = computed<FilterOption[]>(() =>
    TYPES.map((type) => ({ ...type, count: this.counts()[type.id] })),
  );
}
