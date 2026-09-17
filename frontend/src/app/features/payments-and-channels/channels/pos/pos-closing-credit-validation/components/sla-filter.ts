import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';
import { LucideClock } from '@lucide/angular';

import {
  MultiSelectFilterComponent,
  type FilterOption,
} from '../../../../../../shared/ui/multi-select-filter';
import { SLA_DOT, SLA_LABEL, type SlaState } from '../data/sla';

/** Em atraso primeiro: é o que exige acção hoje. */
const ALL_STATES: readonly SlaState[] = ['overdue', 'due-soon', 'on-track', 'settled'];

/** Filtro do «Prazo» em Casos para Análise. */
@Component({
  selector: 'app-sla-filter',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MultiSelectFilterComponent, LucideClock],
  template: `
    <app-multi-select-filter
      label="Prazo"
      allLabel="Todos os prazos"
      allShortLabel="Todos"
      noneLabel="Nenhum"
      [options]="options()"
      [selected]="selected()"
      (changed)="changed.emit($any($event))"
    >
      <svg lucideClock filterIcon [size]="15" [strokeWidth]="2" class="shrink-0"></svg>
    </app-multi-select-filter>
  `,
})
export class SlaFilterComponent {
  readonly counts = input.required<Record<SlaState, number>>();
  readonly selected = input.required<SlaState[]>();
  readonly changed = output<SlaState[]>();
  /** Os prazos que fazem sentido na vista: nos casos em aberto não há «Regularizado». */
  readonly states = input<readonly SlaState[]>(ALL_STATES);

  protected readonly options = computed<FilterOption[]>(() =>
    ALL_STATES.filter((state) => this.states().includes(state)).map((state) => ({
      id: state,
      label: SLA_LABEL[state],
      dot: SLA_DOT[state],
      count: this.counts()[state],
    })),
  );
}
