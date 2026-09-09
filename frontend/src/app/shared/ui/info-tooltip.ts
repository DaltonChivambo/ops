import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  ElementRef,
  inject,
  input,
} from '@angular/core';
import { LucideInfo } from '@lucide/angular';

let nextId = 0;

/**
 * O "i" que explica um termo, em toda a app — um só sítio para o estilo, a
 * cor e o comportamento do popover, para uma mudança valer para todos de
 * uma vez.
 *
 * O popover é anexado directamente ao `<body>`, e não ao lado do ícone: os
 * cartões (`app-collapsible-card`) são `@container`, e isso torna-os bloco
 * de contenção também para `position: fixed` — um popover preso lá dentro
 * nunca conseguiria aparecer por cima de nada fora do cartão (a barra de
 * separadores da tabela, por exemplo). Fora da árvore, mede-se a posição do
 * ícone com `getBoundingClientRect` e decide-se o lado com espaço.
 */
@Component({
  selector: 'app-info-tooltip',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [LucideInfo],
  template: `
    <button
      type="button"
      [attr.aria-label]="label()"
      [attr.aria-describedby]="tooltipId"
      class="inline-flex shrink-0 items-center justify-center rounded-full align-middle text-gray-400 transition-colors hover:bg-moza-50 hover:text-moza-700 focus-visible:bg-moza-50 focus-visible:text-moza-700 focus-visible:outline-none"
      [style.width.px]="size() + 8"
      [style.height.px]="size() + 8"
      [style.margin.px]="-4"
      (mouseenter)="show()"
      (mouseleave)="hide()"
      (focus)="show()"
      (blur)="hide()"
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

  protected readonly tooltipId = `info-tooltip-${nextId++}`;

  private readonly host = inject(ElementRef<HTMLElement>);
  private tooltipEl: HTMLElement | null = null;

  constructor() {
    inject(DestroyRef).onDestroy(() => this.hide());
  }

  protected show(): void {
    if (this.tooltipEl) return;
    const button = this.host.nativeElement.querySelector('button');
    if (!button) return;
    const anchor = button.getBoundingClientRect();

    const el = document.createElement('span');
    el.id = this.tooltipId;
    el.setAttribute('role', 'tooltip');
    el.textContent = this.text();
    el.className =
      'pointer-events-none fixed z-50 w-56 max-w-[80vw] rounded-xl bg-moza-800 px-3.5 py-2.5 text-xs leading-relaxed font-normal text-white shadow-lg sm:w-64';
    document.body.appendChild(el);

    const tip = el.getBoundingClientRect();
    const gap = 8;
    const fitsBelow = anchor.bottom + gap + tip.height <= window.innerHeight;
    const top = fitsBelow ? anchor.bottom + gap : anchor.top - gap - tip.height;
    const left = Math.max(
      gap,
      Math.min(anchor.left + anchor.width / 2 - tip.width / 2, window.innerWidth - tip.width - gap),
    );

    el.style.top = `${Math.max(gap, top)}px`;
    el.style.left = `${left}px`;

    this.tooltipEl = el;
  }

  protected hide(): void {
    this.tooltipEl?.remove();
    this.tooltipEl = null;
  }
}
