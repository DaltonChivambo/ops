import { ChangeDetectionStrategy, Component } from '@angular/core';

/**
 * O cartão branco de que toda a aplicação é feita.
 * Selector de atributo (`<section appCard>`) para preservar a semântica de landmark;
 * as classes vão no `host` para o Angular as juntar às que quem usa acrescentar.
 */
@Component({
  selector: 'section[appCard]',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: '<ng-content />',
  host: {
    class: 'rounded-2xl bg-white p-4 shadow-sm ring-1 ring-gray-100 sm:p-6',
  },
})
export class CardComponent {}
