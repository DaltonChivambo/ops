import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { LucideInfo } from '@lucide/angular';

/**
 * O "i" que explica um termo, em toda a app — um só sítio para o estilo, a
 * cor e o comportamento do popover, para uma mudança valer para todos de uma
 * vez. Botão focável com popover CSS (`group-hover`/`group-focus-within`), e
 * não `title` nativo: aparece no mesmo sítio para o rato e para o teclado, e
 * admite mais do que uma linha de texto.
 */
@Component({
  selector: 'app-info-tooltip',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [LucideInfo],
  template: `
    <span class="group relative inline-flex align-middle">
      <button
        type="button"
        [attr.aria-label]="label()"
        class="inline-flex shrink-0 items-center justify-center rounded-full text-gray-400 transition-colors hover:bg-moza-50 hover:text-moza-700 focus-visible:bg-moza-50 focus-visible:text-moza-700 focus-visible:outline-none"
        [style.width.px]="size() + 8"
        [style.height.px]="size() + 8"
        [style.margin.px]="-4"
      >
        <svg lucideInfo [size]="size()" [strokeWidth]="2"></svg>
      </button>
      <span
        role="tooltip"
        class="pointer-events-none absolute z-20 w-64 rounded-xl bg-moza-800 px-3.5 py-2.5 text-xs leading-relaxed font-normal text-white opacity-0 shadow-lg transition-opacity duration-150 group-hover:opacity-100 group-focus-within:opacity-100 sm:w-72"
        [class]="position()"
      >
        {{ text() }}
      </span>
    </span>
  `,
})
export class InfoTooltipComponent {
  readonly text = input.required<string>();
  readonly label = input('Mais informação');
  /** Tamanho do ícone — o botão cresce à volta dele, sempre com a mesma folga. */
  readonly size = input(11);
  /**
   * Onde o popover se abre a partir do ícone. Por omissão, abaixo e à
   * esquerda — junto a uma linha perto do fundo de um contentor com scroll
   * (a tabela da Reconciliação de Montantes, por exemplo), passa-se `up`
   * para abrir por cima e não ficar cortado.
   */
  readonly openUpward = input(false);

  protected readonly position = () =>
    this.openUpward() ? 'bottom-full left-0 mb-2' : 'top-full left-0 mt-2';
}
