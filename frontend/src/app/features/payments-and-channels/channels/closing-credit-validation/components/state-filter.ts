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
import { LucideCheck, LucideChevronDown, LucideListFilter, LucideMinus } from '@lucide/angular';

import { numberFormatter } from '../../../../../shared/format';
import type { DetailCounts } from '../data/models';
import { ALL_STATES, STATE_OPTIONS, type StateId } from '../data/state-options';

/**
 * Filtro da coluna «Estado» — um botão que abre a lista de caixas, em vez de chips sempre à vista.
 * Devolve sempre a selecção pela ordem de `STATE_OPTIONS`, para o filtro ao servidor ser estável.
 */
@Component({
  selector: 'app-state-filter',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [LucideCheck, LucideChevronDown, LucideListFilter, LucideMinus],
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
      <svg lucideListFilter [size]="15" [strokeWidth]="2" class="shrink-0"></svg>
      {{ label() }}

      @if (!allSelected()) {
        <span
          class="inline-flex size-4 items-center justify-center rounded-full bg-moza-700 text-2xs font-bold text-white tabular-nums"
        >
          {{ n(selected().length) }}
        </span>
      }

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
        class="absolute left-0 z-20 mt-1.5 w-64 overflow-hidden rounded-xl border border-gray-100 bg-white py-1 shadow-lg"
      >
        <!-- Caixa-mestra: traço quando só parte está marcada. -->
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
            (change)="changed.emit(allSelected() ? [] : allStates)"
            class="sr-only"
          />
          <span class="flex-1">Todos os estados</span>
          <span class="text-xs font-medium text-gray-400 tabular-nums">
            {{ n(counts().all) }}
          </span>
        </label>

        <div class="my-1 h-px bg-gray-100"></div>

        @for (option of options; track option.id) {
          @let checked = selected().includes(option.id);

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

            <input
              type="checkbox"
              [checked]="checked"
              (change)="toggle(option.id)"
              class="sr-only"
            />
            <span class="size-2 shrink-0 rounded-[3px]" [class]="option.dot"></span>
            <span class="flex-1 font-medium">{{ option.label }}</span>
            <span class="text-xs text-gray-400 tabular-nums">
              {{ n(option.count(counts())) }}
            </span>
          </label>
        }
      </div>
    }
  `,
})
export class StateFilterComponent {
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);

  readonly counts = input.required<DetailCounts>();
  readonly selected = input.required<StateId[]>();
  readonly changed = output<StateId[]>();

  protected readonly open = signal(false);
  protected readonly options = STATE_OPTIONS;
  protected readonly allStates = ALL_STATES;

  protected readonly allSelected = computed(() => this.selected().length === STATE_OPTIONS.length);

  protected readonly masterState = computed<'on' | 'off' | 'partial'>(() => {
    if (this.allSelected()) return 'on';
    return this.selected().length === 0 ? 'off' : 'partial';
  });

  protected readonly label = computed(() => {
    const selected = this.selected();
    if (this.allSelected()) return 'Todos os estados';
    if (selected.length === 0) return 'Nenhum estado';
    if (selected.length === 1) {
      return STATE_OPTIONS.find((item) => item.id === selected[0])?.label ?? '';
    }
    return `${this.n(selected.length)} de ${this.n(STATE_OPTIONS.length)} estados`;
  });

  protected toggle(id: StateId): void {
    const selected = this.selected();
    this.changed.emit(
      selected.includes(id)
        ? selected.filter((item) => item !== id)
        : // Reconstruir a partir de ALL_STATES mantém a ordem de STATE_OPTIONS,
          // para o filtro que vai ao servidor ser estável entre cliques.
          ALL_STATES.filter((item) => item === id || selected.includes(item)),
    );
  }

  protected onDocumentMouseDown(event: MouseEvent): void {
    if (!this.open()) return;
    if (!this.host.nativeElement.contains(event.target as Node)) this.open.set(false);
  }

  protected n = (value: number) => numberFormatter.format(value);
}
