import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

import { numberFormatter } from '../format';

/**
 * O filtro de ligar e desligar das listas — «mostrar só as linhas que têm X».
 *
 * Irmão do `app-multi-select-filter`, com o mesmo botão: neutro quando está
 * desligado, pintado quando filtra, para se ver de relance que a lista está
 * reduzida. Serve para o que não é um estado entre vários — uma marca que uma
 * linha tem ou não tem.
 *
 * O ícone entra por projecção — `<svg lucideX filterIcon …>` —, como no outro.
 */
@Component({
  selector: 'app-toggle-filter',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { class: 'shrink-0' },
  template: `
    <button
      type="button"
      (click)="toggled.emit()"
      [attr.aria-pressed]="active()"
      class="inline-flex items-center gap-2 rounded-xl border px-3.5 py-2.5 text-sm font-semibold transition-colors"
      [class]="
        active()
          ? 'border-moza-200 bg-moza-50 text-moza-700'
          : 'border-gray-100 bg-gray-50 text-gray-600 hover:text-gray-900'
      "
    >
      <ng-content select="[filterIcon]" />
      {{ label() }}
      @if (count() !== null) {
        <span
          class="rounded-full px-1.5 py-0.5 text-2xs font-bold tabular-nums"
          [class]="active() ? 'bg-moza-100 text-moza-700' : 'bg-gray-200/70 text-gray-500'"
        >
          {{ n(count()!) }}
        </span>
      }
    </button>
  `,
})
export class ToggleFilterComponent {
  readonly label = input.required<string>();
  readonly active = input(false);
  /** Quantas linhas o filtro deixa — `null` para não mostrar número. */
  readonly count = input<number | null>(null);

  readonly toggled = output<void>();

  protected n = (value: number) => numberFormatter.format(value);
}
