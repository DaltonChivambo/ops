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
import { NgTemplateOutlet } from '@angular/common';
import {
  LucideCheck,
  LucideChevronDown,
  LucideCircleCheck,
  LucideCircleDot,
  LucideLayers,
} from '@lucide/angular';

import { numberFormatter } from '../../../../../../shared/format';

/** Que casos a lista mostra. Em aberto é a fila de trabalho; regularizados é o histórico. */
export type CaseView = 'all' | 'open' | 'resolved';

const OPTIONS: ReadonlyArray<{ id: CaseView; label: string; hint: string }> = [
  { id: 'open', label: 'Casos em aberto', hint: 'Pendentes e em análise' },
  { id: 'resolved', label: 'Casos regularizados', hint: 'Já tratados' },
  { id: 'all', label: 'Todos os casos', hint: 'Em aberto e regularizados' },
];

/**
 * O selector da lista — escolhe-se UMA vista, e é o primeiro controlo da barra:
 * decide o que os filtros ao lado filtram. Mesmo desenho dos filtros (botão e
 * painel), mas com marca de escolha em vez de caixas, porque não se combina.
 */
@Component({
  selector: 'app-case-view-select',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    NgTemplateOutlet,
    LucideCheck,
    LucideChevronDown,
    LucideCircleCheck,
    LucideCircleDot,
    LucideLayers,
  ],
  host: {
    class: 'relative shrink-0',
    '(document:mousedown)': 'onDocumentMouseDown($event)',
    '(document:keydown.escape)': 'open.set(false)',
  },
  template: `
    <button
      type="button"
      (click)="open.set(!open())"
      aria-haspopup="listbox"
      [attr.aria-expanded]="open()"
      class="inline-flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-3.5 py-2.5 text-sm font-semibold text-gray-900 shadow-xs transition-colors hover:border-gray-300"
    >
      <ng-container [ngTemplateOutlet]="icon" [ngTemplateOutletContext]="{ $implicit: value() }" />
      {{ current().label }}
      <span
        class="rounded-md bg-gray-100 px-1.5 py-0.5 text-2xs font-bold text-gray-600 tabular-nums"
      >
        {{ n(counts()[value()]) }}
      </span>
      <svg
        lucideChevronDown
        [size]="14"
        [strokeWidth]="2.4"
        class="shrink-0 text-gray-400 transition-transform"
        [class.rotate-180]="open()"
      ></svg>
    </button>

    @if (open()) {
      <ul
        role="listbox"
        aria-label="Casos a mostrar"
        class="absolute left-0 z-20 mt-1.5 w-64 overflow-hidden rounded-xl border border-gray-100 bg-white py-1 shadow-lg"
      >
        @for (option of options; track option.id) {
          @let selected = option.id === value();
          <li role="option" [attr.aria-selected]="selected">
            <button
              type="button"
              (click)="choose(option.id)"
              class="flex w-full items-center gap-2.5 px-3 py-2 text-left transition-colors hover:bg-gray-50"
              [class.bg-moza-50]="selected"
            >
              <ng-container
                [ngTemplateOutlet]="icon"
                [ngTemplateOutletContext]="{ $implicit: option.id }"
              />
              <span class="min-w-0 flex-1">
                <span class="block text-sm font-semibold text-gray-900">{{ option.label }}</span>
                <span class="block text-2xs text-gray-400">{{ option.hint }}</span>
              </span>
              <span class="text-xs text-gray-400 tabular-nums">{{ n(counts()[option.id]) }}</span>
              <span class="inline-flex w-4 justify-center text-moza-700">
                @if (selected) {
                  <svg lucideCheck [size]="15" [strokeWidth]="2.8"></svg>
                }
              </span>
            </button>
          </li>
        }
      </ul>
    }

    <ng-template #icon let-view>
      @switch (view) {
        @case ('open') {
          <svg
            lucideCircleDot
            [size]="16"
            [strokeWidth]="2.2"
            class="shrink-0 text-amber-600"
          ></svg>
        }
        @case ('resolved') {
          <svg
            lucideCircleCheck
            [size]="16"
            [strokeWidth]="2.2"
            class="shrink-0 text-emerald-600"
          ></svg>
        }
        @default {
          <svg lucideLayers [size]="16" [strokeWidth]="2.2" class="shrink-0 text-gray-500"></svg>
        }
      }
    </ng-template>
  `,
})
export class CaseViewSelectComponent {
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);

  readonly value = input.required<CaseView>();
  readonly counts = input.required<Record<CaseView, number>>();
  readonly changed = output<CaseView>();

  protected readonly open = signal(false);
  protected readonly options = OPTIONS;
  protected readonly current = computed(
    () => OPTIONS.find((option) => option.id === this.value()) ?? OPTIONS[0],
  );

  protected choose(view: CaseView): void {
    this.open.set(false);
    if (view !== this.value()) this.changed.emit(view);
  }

  protected onDocumentMouseDown(event: MouseEvent): void {
    if (!this.open()) return;
    if (!this.host.nativeElement.contains(event.target as Node)) this.open.set(false);
  }

  protected n = (value: number) => numberFormatter.format(value);
}
