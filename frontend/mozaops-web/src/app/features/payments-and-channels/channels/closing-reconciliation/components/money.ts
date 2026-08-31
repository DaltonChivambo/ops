import { ChangeDetectionStrategy, Component, input } from '@angular/core';

import { formatAmount } from '../../../../../shared/format';

/** Um montante em MZN, ou travessão quando não há valor — `null` é ausência de crédito, não zero. */
@Component({
  selector: 'app-money',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @let v = value();
    @if (v === null) {
      <span class="text-gray-300">—</span>
    } @else {
      <span class="font-semibold text-gray-900 tabular-nums">
        {{ amount(v) }}<span class="ml-1 text-[0.7em] font-normal text-gray-400">MZN</span>
      </span>
    }
  `,
})
export class MoneyComponent {
  readonly value = input.required<number | null>();
  protected amount = formatAmount;
}
