import {
  booleanAttribute,
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';

/**
 * O cartão branco de que toda a aplicação é feita.
 * Selector de atributo (`<section appCard>`) para preservar a semântica de landmark;
 * as classes vão no `host` para o Angular as juntar às que quem usa acrescentar.
 *
 * `compact` para cartões pequenos em grelha, como os indicadores: a margem
 * interior vai por input porque duas classes de padding em conflito ganham
 * pela ordem do CSS, não pela do atributo.
 */
@Component({
  selector: 'section[appCard]',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: '<ng-content />',
  host: {
    class: 'rounded-2xl bg-white shadow-sm ring-1 ring-gray-100',
    '[class]': 'padding()',
  },
})
export class CardComponent {
  readonly compact = input(false, { transform: booleanAttribute });

  protected readonly padding = computed(() => (this.compact() ? 'p-4 2xl:p-5' : 'p-4 sm:p-6'));
}
