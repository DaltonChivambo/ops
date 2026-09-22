import { DestroyRef, Directive, ElementRef, inject, input, signal } from '@angular/core';

let nextId = 0;

/**
 * A caixa escura que explica um termo, em qualquer elemento — a mesma do "i"
 * (`app-info-tooltip`, que a usa por baixo), para quem já mostra o termo na
 * página e só lhe falta a explicação: a pastilha do período numa tabela, por
 * exemplo, onde um "i" ao lado seria mais ruído do que ajuda. Existe para não
 * haver um segundo estilo de informação — o `title` do browser, cinzento,
 * lento a aparecer e impossível de tocar — a viver ao lado deste.
 *
 * O popover é anexado directamente ao `<body>`, e não ao lado do elemento: os
 * cartões (`app-collapsible-card`) são `@container`, e isso torna-os bloco de
 * contenção também para `position: fixed` — um popover preso lá dentro nunca
 * conseguiria aparecer por cima de nada fora do cartão. Fora da árvore,
 * mede-se a posição do elemento com `getBoundingClientRect` e decide-se o
 * lado com espaço.
 */
/**
 * `capture` apanha o scroll de qualquer contentor (tabelas com scroll próprio
 * incluídas) — o evento não sobe por bolha, só por captura. `passive` porque o
 * handler só esconde: o browser não tem de o esperar para rolar.
 */
const SCROLL_LISTENER = { capture: true, passive: true } as const;

@Directive({
  selector: '[appTooltip]',
  host: {
    '[attr.aria-describedby]': 'describedBy()',
    '(mouseenter)': 'show()',
    '(mouseleave)': 'hide()',
    '(focus)': 'show()',
    '(blur)': 'hide()',
  },
})
export class TooltipDirective {
  /**
   * Aceita `null` para quem só tem explicação em alguns casos — a diferença
   * que está a zero, por exemplo. Sem texto, não há caixa.
   */
  readonly text = input.required<string | null>({ alias: 'appTooltip' });

  private readonly tooltipId = `app-tooltip-${nextId++}`;

  /**
   * Só aponta para o popover enquanto ele existe: um `aria-describedby` fixo
   * ficaria a apontar para um id que não está no documento.
   */
  protected readonly describedBy = signal<string | null>(null);

  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);
  private tooltipEl: HTMLElement | null = null;

  /**
   * Fecha ao rolar em vez de seguir o elemento: preso ao `<body>`, a posição
   * fica onde nasceu — sem isto, "arrastava-se" ecrã afora até a rolagem
   * parar e um novo hit-test finalmente disparar o `mouseleave`.
   */
  private readonly onScroll = () => this.hide();

  constructor() {
    inject(DestroyRef).onDestroy(() => this.hide());
  }

  protected show(): void {
    if (this.tooltipEl) return;
    const text = this.text();
    if (!text) return;
    const anchor = this.host.nativeElement.getBoundingClientRect();

    const el = document.createElement('span');
    el.id = this.tooltipId;
    el.setAttribute('role', 'tooltip');
    el.textContent = text;
    // A caixa tem o tamanho do que lhe puseram dentro: `w-max` encolhe até ao
    // texto, e o tecto só entra quando ele é uma frase — a descrição de um "i"
    // quebra nas mesmas 14rem de sempre, e um "Período 352" fica do tamanho de
    // "Período 352". Largura fixa aqui dava um cartaz para dizer duas palavras.
    el.className =
      'pointer-events-none fixed z-50 w-max max-w-56 rounded-xl bg-moza-800 px-3.5 py-2.5 text-xs leading-relaxed font-normal text-white shadow-lg sm:max-w-64';
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
    this.describedBy.set(this.tooltipId);
    window.addEventListener('scroll', this.onScroll, SCROLL_LISTENER);
  }

  protected hide(): void {
    window.removeEventListener('scroll', this.onScroll, SCROLL_LISTENER);
    this.tooltipEl?.remove();
    this.tooltipEl = null;
    this.describedBy.set(null);
  }
}
