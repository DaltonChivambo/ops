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
import { LucideChevronDown } from '@lucide/angular';

import { numberFormatter } from '../format';
import { CheckboxComponent } from './checkbox';

/** Uma opção do filtro: o que se mostra, a cor que a identifica, e quantas linhas tem. */
export interface FilterOption {
  readonly id: string;
  readonly label: string;
  /** Classe da marca de cor, a mesma que as linhas usam (ex.: `bg-amber-500`). */
  readonly dot: string;
  readonly count: number;
}

/**
 * O filtro de selecção múltipla das listas: um botão que diz o que está
 * escolhido, e abre as opções com caixa, cor e contagem — em vez de chips
 * sempre à vista, que ocupavam a barra inteira e liam-se como números soltos.
 *
 * Todas marcadas é o mesmo que sem filtro, e o botão fica neutro; qualquer
 * outra escolha pinta-o, para se ver de relance que a lista está filtrada.
 *
 * A selecção sai sempre pela ordem das `options`, e não pela ordem dos cliques:
 * é ela que vai ao servidor ou a uma chave de cache, e tem de ser estável.
 *
 * O ícone entra por projecção — `<svg lucideClock filterIcon …>` —, para cada
 * filtro dizer o que filtra sem o componente conhecer os ícones todos.
 */
@Component({
  selector: 'app-multi-select-filter',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CheckboxComponent, LucideChevronDown],
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
      <ng-content select="[filterIcon]" />
      <span class="font-medium opacity-60">{{ label() }}:</span>
      {{ summary() }}
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
          <app-checkbox
            [checked]="allSelected()"
            [indeterminate]="!allSelected() && selected().length > 0"
            (toggled)="changed.emit(allSelected() ? [] : allIds())"
          />
          <span class="flex-1">{{ allLabel() }}</span>
          <span class="text-xs font-medium text-gray-400 tabular-nums">{{ n(total()) }}</span>
        </label>

        <div class="my-1 h-px bg-gray-100"></div>

        @for (option of options(); track option.id) {
          <label
            class="flex cursor-pointer items-center gap-2.5 px-3 py-2 text-sm text-gray-600 transition-colors hover:bg-gray-50"
          >
            <app-checkbox
              [checked]="selected().includes(option.id)"
              (toggled)="toggle(option.id)"
            />
            <span class="size-2 shrink-0 rounded-full" [class]="option.dot"></span>
            <span class="flex-1 font-medium">{{ option.label }}</span>
            <span class="text-xs text-gray-400 tabular-nums">{{ n(option.count) }}</span>
          </label>
        }
      </div>
    }
  `,
})
export class MultiSelectFilterComponent {
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);

  /** O que se filtra, curto — sai no botão como «Validação: …». */
  readonly label = input.required<string>();
  /** A linha da caixa-mestra — «Todas as validações». */
  readonly allLabel = input.required<string>();
  /** O género conta: «Todas»/«Nenhuma» para fases e validações, «Todos»/«Nenhum» para prazos. */
  readonly allShortLabel = input('Todas');
  readonly noneLabel = input('Nenhuma');

  readonly options = input.required<readonly FilterOption[]>();
  readonly selected = input.required<readonly string[]>();
  readonly changed = output<string[]>();

  protected readonly open = signal(false);

  protected readonly allIds = computed(() => this.options().map((option) => option.id));
  protected readonly total = computed(() =>
    this.options().reduce((sum, option) => sum + option.count, 0),
  );
  protected readonly allSelected = computed(() => this.selected().length === this.options().length);

  protected readonly summary = computed(() => {
    const selected = this.selected();
    if (this.allSelected()) return this.allShortLabel();
    if (selected.length === 0) return this.noneLabel();
    if (selected.length === 1) {
      return this.options().find((option) => option.id === selected[0])?.label ?? '';
    }
    return `${this.n(selected.length)} de ${this.n(this.options().length)}`;
  });

  protected toggle(id: string): void {
    const selected = this.selected();
    this.changed.emit(
      selected.includes(id)
        ? selected.filter((item) => item !== id)
        : this.allIds().filter((item) => item === id || selected.includes(item)),
    );
  }

  protected onDocumentMouseDown(event: MouseEvent): void {
    if (!this.open()) return;
    if (!this.host.nativeElement.contains(event.target as Node)) this.open.set(false);
  }

  protected n = (value: number) => numberFormatter.format(value);
}
