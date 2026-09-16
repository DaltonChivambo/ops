import {
  ChangeDetectionStrategy,
  Component,
  computed,
  ElementRef,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { LucideCheck, LucideChevronDown, LucideCircleDot, LucideMinus } from '@lucide/angular';

import { numberFormatter } from '../../../../../../shared/format';
import { CASE_STATUSES, CASE_STATUS_DOT, CASE_STATUS_LABEL } from '../data/case-status';
import type { CaseStatus } from '../data/models';

/**
 * Filtro da «Fase» do tratamento em Casos para Análise — o mesmo padrão do filtro de tipo e
 * do de prazo. Substitui a fila de separadores: cinco botões com contadores
 * ocupavam a barra inteira e liam-se como números soltos, e aqui cabe também
 * escolher mais de um («pendentes e em análise interna»).
 */
@Component({
  selector: 'app-case-status-filter',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [LucideCheck, LucideChevronDown, LucideCircleDot, LucideMinus],
  host: {
    class: 'relative shrink-0',
    '(document:mousedown)': 'onDocumentMouseDown($event)',
    '(document:keydown.escape)': 'open.set(false)',
  },
  template: `
    <button
      type="button"
      (click)="open.set(!open())"
      aria-haspopup="true"
      [attr.aria-expanded]="open()"
      class="inline-flex items-center gap-2 rounded-xl border px-3.5 py-2.5 text-sm font-semibold transition-colors"
      [class]="
        allSelected()
          ? 'border-gray-100 bg-gray-50 text-gray-600 hover:text-gray-900'
          : 'border-moza-200 bg-moza-50 text-moza-700'
      "
    >
      <svg lucideCircleDot [size]="15" [strokeWidth]="2" class="shrink-0"></svg>
      <span class="font-medium opacity-60">Fase:</span>
      {{ label() }}

      <svg
        lucideChevronDown
        [size]="14"
        [strokeWidth]="2.4"
        class="shrink-0 text-gray-400 transition-transform"
        [class.rotate-180]="open()"
      ></svg>
    </button>

    @if (open()) {
      <div
        class="absolute left-0 z-20 mt-1.5 w-60 overflow-hidden rounded-xl border border-gray-100 bg-white py-1 shadow-lg"
      >
        <label
          class="flex cursor-pointer items-center gap-2.5 px-3 py-2 text-sm font-semibold text-gray-900 transition-colors hover:bg-gray-50"
        >
          <span
            class="inline-flex size-4 shrink-0 items-center justify-center rounded border transition-colors"
            [class]="
              masterState() === 'off'
                ? 'border-gray-300 bg-white'
                : 'border-moza-700 bg-moza-700 text-white'
            "
          >
            @if (masterState() === 'on') {
              <svg lucideCheck [size]="11" [strokeWidth]="3.5"></svg>
            } @else if (masterState() === 'partial') {
              <svg lucideMinus [size]="11" [strokeWidth]="3.5"></svg>
            }
          </span>

          <input
            type="checkbox"
            [checked]="allSelected()"
            [indeterminate]="masterState() === 'partial'"
            (change)="changed.emit(allSelected() ? [] : [...statuses()])"
            class="sr-only"
          />
          <span class="flex-1">Todas as fases</span>
          <span class="text-xs font-medium text-gray-400 tabular-nums">{{ n(total()) }}</span>
        </label>

        <div class="my-1 h-px bg-gray-100"></div>

        @for (status of statuses(); track status) {
          @let checked = selected().includes(status);

          <label
            class="flex cursor-pointer items-center gap-2.5 px-3 py-2 text-sm text-gray-600 transition-colors hover:bg-gray-50"
          >
            <span
              class="inline-flex size-4 shrink-0 items-center justify-center rounded border transition-colors"
              [class]="
                checked ? 'border-moza-700 bg-moza-700 text-white' : 'border-gray-300 bg-white'
              "
            >
              @if (checked) {
                <svg lucideCheck [size]="11" [strokeWidth]="3.5"></svg>
              }
            </span>

            <input type="checkbox" [checked]="checked" (change)="toggle(status)" class="sr-only" />
            <span class="size-2 shrink-0 rounded-full" [class]="dot[status]"></span>
            <span class="flex-1 font-medium">{{ labels[status] }}</span>
            <span class="text-xs text-gray-400 tabular-nums">{{ n(counts()[status]) }}</span>
          </label>
        }
      </div>
    }
  `,
})
export class CaseStatusFilterComponent {
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);

  readonly counts = input.required<Record<CaseStatus, number>>();
  readonly selected = input.required<CaseStatus[]>();
  readonly changed = output<CaseStatus[]>();
  /** Os estados que fazem sentido na vista — nos casos em aberto, sem «Regularizado». */
  readonly statuses = input<readonly CaseStatus[]>(CASE_STATUSES);

  protected readonly open = signal(false);
  protected readonly labels = CASE_STATUS_LABEL;
  protected readonly dot = CASE_STATUS_DOT;

  protected readonly total = computed(() =>
    this.statuses().reduce((sum, status) => sum + this.counts()[status], 0),
  );

  protected readonly allSelected = computed(
    () => this.selected().length === this.statuses().length,
  );

  protected readonly masterState = computed<'on' | 'off' | 'partial'>(() => {
    if (this.allSelected()) return 'on';
    return this.selected().length === 0 ? 'off' : 'partial';
  });

  protected readonly label = computed(() => {
    const selected = this.selected();
    if (this.allSelected()) return 'Todas';
    if (selected.length === 0) return 'Nenhuma';
    if (selected.length === 1) return CASE_STATUS_LABEL[selected[0]];
    return `${this.n(selected.length)} de ${this.n(this.statuses().length)}`;
  });

  protected toggle(status: CaseStatus): void {
    const selected = this.selected();
    this.changed.emit(
      selected.includes(status)
        ? selected.filter((item) => item !== status)
        : this.statuses().filter((item) => item === status || selected.includes(item)),
    );
  }

  protected onDocumentMouseDown(event: MouseEvent): void {
    if (!this.open()) return;
    if (!this.host.nativeElement.contains(event.target as Node)) this.open.set(false);
  }

  protected n = (value: number) => numberFormatter.format(value);
}
