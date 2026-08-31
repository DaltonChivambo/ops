import { DestroyRef, Directive, ElementRef, inject, input } from '@angular/core';

/**
 * `deltaMode` 1 conta linhas (Firefox); 0 conta píxeis. Sem isto o Firefox
 * ficava ~16× mais lento.
 */
const LINE_HEIGHT_PX = 16;

/** Píxeis de um «tique» de roda, seja qual for a unidade que o browser reporta. */
function pixelsOf(event: WheelEvent): number {
  if (event.deltaMode === 1) return event.deltaY * LINE_HEIGHT_PX;
  // `deltaMode` 2 conta ecrãs — raro, mas tomado à letra dava um salto absurdo.
  if (event.deltaMode === 2) return event.deltaY * window.innerHeight;
  return event.deltaY;
}

/**
 * Duas fases ao descer a roda sobre uma lista com scroll próprio: primeiro sobe a
 * PÁGINA até a âncora encostar ao topo, só depois corre a lista — por omissão o
 * browser faz o oposto e a lista fica encaixotada a meio do ecrã.
 * Só cobre `wheel`; regista o listener à mão porque o `host` do Angular não
 * passa `passive: false`, e sem isso o `preventDefault` é ignorado.
 */
@Directive({
  selector: '[appPageFirstScroll]',
})
export class PageFirstScrollDirective {
  /** O que tem de encostar ao topo do ecrã antes de a lista começar a correr. */
  readonly anchor = input.required<HTMLElement | undefined>({ alias: 'appPageFirstScroll' });

  constructor() {
    const box = inject<ElementRef<HTMLElement>>(ElementRef).nativeElement;

    const onWheel = (event: WheelEvent) => {
      const delta = pixelsOf(event);
      const distanceToTop = this.anchor()?.getBoundingClientRect().top ?? 0;
      // Sem isto, chegar ao fim da página com a âncora a 1-2px do topo desviava o
      // gesto para uma página que já não anda, e a lista nunca começava a correr.
      const pageRoom = document.documentElement.scrollHeight - innerHeight - window.scrollY;

      if (delta > 0 && distanceToTop > 0 && pageRoom > 0) {
        event.preventDefault();
        window.scrollBy(0, Math.min(delta, distanceToTop, pageRoom));
        return;
      }

      // A subir com a lista já no início: desce a página em vez de o gesto ficar
      // preso pelo latching da roda.
      if (delta < 0 && box.scrollTop <= 0 && window.scrollY > 0) {
        event.preventDefault();
        window.scrollBy(0, Math.max(delta, -window.scrollY));
      }
    };

    box.addEventListener('wheel', onWheel, { passive: false });
    inject(DestroyRef).onDestroy(() => box.removeEventListener('wheel', onWheel));
  }
}
