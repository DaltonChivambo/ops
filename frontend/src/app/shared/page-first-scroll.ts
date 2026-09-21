import { DestroyRef, Directive, ElementRef, inject, input } from '@angular/core';

/** `deltaMode` 1 conta linhas (Firefox); 0 conta píxeis. */
const LINE_HEIGHT_PX = 16;

/** A roda parada por mais do que isto começa um gesto novo. */
const GESTURE_GAP_MS = 120;

/**
 * Folga do ponto de passagem entre a página e a lista.
 *
 * O `getBoundingClientRect` devolve píxeis CSS fraccionários e o scroll assenta
 * em píxeis do ecrã — com o DPI a 125% a diferença anda à volta de 1px. Um
 * limiar mais apertado punha a decisão a mudar de tique para tique.
 */
const SETTLED_PX = 2;

export type ScrollPhase = 'page' | 'list';

export interface ScrollRoom {
  /** Quanto falta à âncora para assentar no topo. */
  readonly toAnchor: number;
  /** Quanto a página ainda pode descer. */
  readonly belowPage: number;
  readonly listOffset: number;
  readonly pageOffset: number;
}

/** Quem leva este tique da roda: a página ou a lista. */
export function phaseFor(delta: number, room: ScrollRoom): ScrollPhase {
  if (delta > 0) {
    return room.toAnchor > SETTLED_PX && room.belowPage > 0 ? 'page' : 'list';
  }
  return room.listOffset <= 0 && room.pageOffset > 0 ? 'page' : 'list';
}

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
 * A fase decide-se uma vez por gesto e nunca volta atrás. Reavaliar a cada
 * tique punha a página e a lista a alternar à volta do ponto de passagem —
 * uma no main thread com `preventDefault`, a outra no compositor — e isso
 * via-se a tremer.
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

  private phase: ScrollPhase | null = null;
  private direction = 0;
  private lastWheelAt = 0;
  private anchorRestsAt: number | null = null;

  constructor() {
    const box = inject<ElementRef<HTMLElement>>(ElementRef).nativeElement;

    const onWheel = (event: WheelEvent) => {
      const delta = pixelsOf(event);
      if (delta === 0) return;

      this.openGesture(event.timeStamp, Math.sign(delta));
      if (this.phase === 'list') return;

      const room = this.roomAround(box);
      this.phase = phaseFor(delta, room);
      if (this.phase === 'list') return;

      event.preventDefault();
      const step =
        delta > 0
          ? Math.min(delta, room.toAnchor, room.belowPage)
          : Math.max(delta, -room.pageOffset);
      window.scrollBy({ top: step, behavior: 'instant' });

      // O que sobra do tique em que a âncora assenta vai para a lista: sem
      // isto a passagem perde um tique e sente-se como um tranco.
      box.scrollTop += delta - step;
    };

    box.addEventListener('wheel', onWheel, { passive: false });
    inject(DestroyRef).onDestroy(() => box.removeEventListener('wheel', onWheel));
  }

  private openGesture(at: number, direction: number): void {
    const continues = at - this.lastWheelAt <= GESTURE_GAP_MS && direction === this.direction;
    this.lastWheelAt = at;
    if (continues) return;

    this.phase = null;
    this.direction = direction;
    this.anchorRestsAt = null;
  }

  private roomAround(box: HTMLElement): ScrollRoom {
    const anchor = this.anchor();
    return {
      toAnchor: anchor ? anchor.getBoundingClientRect().top - this.restsAt(anchor) : 0,
      belowPage: document.documentElement.scrollHeight - window.innerHeight - window.scrollY,
      listOffset: box.scrollTop,
      pageOffset: window.scrollY,
    };
  }

  /**
   * Uma âncora `sticky` não chega ao topo do ecrã: pára no seu próprio `top`.
   * Lê-se uma vez por gesto — não muda lá dentro, e o `getComputedStyle` força
   * recálculo de estilo a cada tique.
   */
  private restsAt(anchor: HTMLElement): number {
    if (this.anchorRestsAt === null) {
      const style = getComputedStyle(anchor);
      this.anchorRestsAt = style.position === 'sticky' ? parseFloat(style.top) || 0 : 0;
    }
    return this.anchorRestsAt;
  }
}
