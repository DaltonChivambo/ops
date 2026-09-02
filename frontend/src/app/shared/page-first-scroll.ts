import { DestroyRef, Directive, ElementRef, inject, input } from '@angular/core';

/** `deltaMode` 1 conta linhas (Firefox); 0 conta píxeis. */
const LINE_HEIGHT_PX = 16;

/** Píxeis de um «tique» de roda, seja qual for a unidade que o browser reporta. */
function pixelsOf(event: WheelEvent): number {
  if (event.deltaMode === 1) return event.deltaY * LINE_HEIGHT_PX;
  // `deltaMode` 2 conta ecrãs.
  if (event.deltaMode === 2) return event.deltaY * window.innerHeight;
  return event.deltaY;
}

/**
 * Duas fases ao descer a roda sobre uma lista com scroll próprio: primeiro sobe
 * a PÁGINA até a âncora assentar, só depois corre a lista.
 *
 * O listener regista-se à mão porque o `host` do Angular não passa
 * `passive: false`, e sem isso o `preventDefault` é ignorado.
 */
@Directive({
  selector: '[appPageFirstScroll]',
})
export class PageFirstScrollDirective {
  /** O que tem de encostar ao topo do ecrã antes de a lista começar a correr. */
  readonly anchor = input.required<HTMLElement | undefined>({ alias: 'appPageFirstScroll' });

  /**
   * Quanto falta à âncora para assentar. Uma âncora `sticky` não chega ao topo
   * do ecrã: pára no seu próprio `top`, que abaixo do lg nem é zero.
   */
  private pendingDistance(anchor: HTMLElement): number {
    const style = getComputedStyle(anchor);
    const restsAt = style.position === 'sticky' ? parseFloat(style.top) || 0 : 0;
    return anchor.getBoundingClientRect().top - restsAt;
  }

  constructor() {
    const box = inject<ElementRef<HTMLElement>>(ElementRef).nativeElement;

    const onWheel = (event: WheelEvent) => {
      const delta = pixelsOf(event);
      const anchor = this.anchor();
      const distanceToTop = anchor ? this.pendingDistance(anchor) : 0;
      const pageRoom = document.documentElement.scrollHeight - innerHeight - window.scrollY;

      // Margem de 1px para o arredondamento sub-pixel.
      if (delta > 0 && distanceToTop > 1 && pageRoom > 0) {
        event.preventDefault();
        window.scrollBy(0, Math.min(delta, distanceToTop, pageRoom));
        return;
      }

      // A subir com a lista no início: desce a página.
      if (delta < 0 && box.scrollTop <= 0 && window.scrollY > 0) {
        event.preventDefault();
        window.scrollBy(0, Math.max(delta, -window.scrollY));
      }
    };

    box.addEventListener('wheel', onWheel, { passive: false });
    inject(DestroyRef).onDestroy(() => box.removeEventListener('wheel', onWheel));
  }
}
