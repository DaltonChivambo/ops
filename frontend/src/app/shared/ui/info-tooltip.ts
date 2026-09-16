import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { LucideInfo } from '@lucide/angular';

import { TooltipDirective } from './tooltip';

/**
 * O "i" que explica um termo, em toda a app — um só sítio para o estilo, a
 * cor e o comportamento do ícone, para uma mudança valer para todos de uma
 * vez. A caixa que aparece é a de `appTooltip`, partilhada com quem não
 * precisa do ícone porque o termo já está escrito na página.
 */
@Component({
  selector: 'app-info-tooltip',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [LucideInfo, TooltipDirective],
  template: `
    <button
      type="button"
      [appTooltip]="text()"
      [attr.aria-label]="label()"
      class="inline-flex shrink-0 items-center justify-center rounded-full align-middle text-gray-400 transition-colors hover:bg-moza-50 hover:text-moza-700 focus-visible:bg-moza-50 focus-visible:text-moza-700 focus-visible:outline-none"
      [style.width.px]="size() + 8"
      [style.height.px]="size() + 8"
      [style.margin.px]="-4"
    >
      <svg lucideInfo [size]="size()" [strokeWidth]="2"></svg>
    </button>
  `,
})
export class InfoTooltipComponent {
  readonly text = input.required<string>();
  readonly label = input('Mais informação');
  /** Tamanho do ícone — o botão cresce à volta dele, sempre com a mesma folga. */
  readonly size = input(11);
}
