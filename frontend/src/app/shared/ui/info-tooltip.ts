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
        class="pointer-events-none absolute z-20 w-56 max-w-[80vw] rounded-xl bg-moza-800 px-3.5 py-2.5 text-xs leading-relaxed font-normal text-white opacity-0 shadow-lg transition-opacity duration-150 group-hover:opacity-100 group-focus-within:opacity-100 sm:w-64"
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
   * Abre por baixo e centrado no ícone, por omissão — centrado porque o
   * ícone raramente está a meio da tela, e um popover ancorado só de um
   * lado (ex.: `left-0`) cortava-se na borda de tabelas com scroll
   * horizontal (`overflow-x-auto`), como a da Reconciliação de Montantes.
   * Junto ao fundo de um contentor (a última linha de uma tabela, o Total),
   * passa-se `true` para abrir por cima em vez de por baixo.
   */
  readonly openUpward = input(false);

  protected readonly position = () =>
    this.openUpward()
      ? 'bottom-full left-1/2 mb-2 -translate-x-1/2'
      : 'top-full left-1/2 mt-2 -translate-x-1/2';
}
