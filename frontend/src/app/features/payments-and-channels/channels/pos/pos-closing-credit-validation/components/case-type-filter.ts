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

import { numberFormatter } from '../../../../../../shared/format';
import type { CaseType } from '../data/models';

/** Mesma prioridade usada em todo o ecrã: incorrecto, duplicado, não creditado. */
const OPTIONS: ReadonlyArray<{ id: CaseType; label: string; dot: string }> = [
  { id: 'mismatch', label: 'Incorrecto', dot: 'bg-alert-500' },
  { id: 'duplicated', label: 'Duplicados', dot: 'bg-amber-500' },
  { id: 'missing', label: 'Não creditado', dot: 'bg-moza-500' },
];
const ALL_TYPES = OPTIONS.map((option) => option.id);

/**
 * Filtro do «Tipo» em Casos para Análise — o mesmo padrão do app-state-filter
 * (Todos os Fechos), adaptado aos três tipos de caso em vez dos cinco estados.
 */
@Component({
  selector: 'app-case-type-filter',
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
        class="absolute left-0 z-20 mt-1.5 w-56 overflow-hidden rounded-xl border border-gray-100 bg-white py-1 shadow-lg"
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
            (change)="changed.emit(allSelected() ? [] : allTypes)"
            class="sr-only"
          />
          <span class="flex-1">Todos os tipos</span>
          <span class="text-xs font-medium text-gray-400 tabular-nums">{{ n(total()) }}</span>
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
            <span class="text-xs text-gray-400 tabular-nums">{{ n(counts()[option.id]) }}</span>
          </label>
        }
      </div>
    }
  `,
})
export class CaseTypeFilterComponent {
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);

  readonly counts = input.required<Record<CaseType, number>>();
  readonly selected = input.required<CaseType[]>();
  readonly changed = output<CaseType[]>();

  protected readonly open = signal(false);
  protected readonly options = OPTIONS;
  protected readonly allTypes = ALL_TYPES;

  protected readonly total = computed(() =>
    Object.values(this.counts()).reduce((sum, count) => sum + count, 0),
  );

  protected readonly allSelected = computed(() => this.selected().length === OPTIONS.length);

  protected readonly masterState = computed<'on' | 'off' | 'partial'>(() => {
    if (this.allSelected()) return 'on';
    return this.selected().length === 0 ? 'off' : 'partial';
  });

  protected readonly label = computed(() => {
    const selected = this.selected();
    if (this.allSelected()) return 'Todos os tipos';
    if (selected.length === 0) return 'Nenhum tipo';
    if (selected.length === 1) {
      return OPTIONS.find((option) => option.id === selected[0])?.label ?? '';
    }
    return `${this.n(selected.length)} de ${this.n(OPTIONS.length)} tipos`;
  });

  protected toggle(id: CaseType): void {
    const selected = this.selected();
    this.changed.emit(
      selected.includes(id)
        ? selected.filter((item) => item !== id)
        : ALL_TYPES.filter((item) => item === id || selected.includes(item)),
    );
  }

  protected onDocumentMouseDown(event: MouseEvent): void {
    if (!this.open()) return;
    if (!this.host.nativeElement.contains(event.target as Node)) this.open.set(false);
  }

  protected n = (value: number) => numberFormatter.format(value);
}
