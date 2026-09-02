import { ChangeDetectionStrategy, Component, computed, input, model } from '@angular/core';

/** Um segmento da barra. A cor vem em classe porque é sempre uma cor do tema. */
export interface BarSegment {
  readonly key: string;
  readonly label: string;
  readonly value: number;
  /** Classe de fundo, ex.: `bg-emerald-500`. */
  readonly className: string;
  /** Já formatado: o gráfico não conhece moedas. */
  readonly ariaLabel: string;
}

/**
 * Barra empilhada de proporções, com destaque bidireccional — quem a usa tem
 * uma tabela ao lado, e apontar a um segmento tem de acender a linha.
 *
 * A largura mínima existe porque as fatias que interessam são fracções de ponto
 * percentual. As pontas arredonda-as o contentor, não os segmentos: um segmento
 * mais estreito do que o raio sairia cortado contra o canto.
 */
@Component({
  selector: 'app-stacked-bar',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div
      class="flex h-3 w-full gap-px overflow-hidden rounded-full bg-gray-100"
      (mouseleave)="active.set(null)"
    >
      @for (segment of segments(); track segment.key) {
        @let on = active() === segment.key;
        <button
          type="button"
          [class]="segment.className + ' cursor-pointer transition-opacity duration-200'"
          [style.width.%]="widthOf(segment)"
          [style.minWidth.rem]="0.625"
          [style.opacity]="active() && !on ? 0.25 : 1"
          [attr.aria-label]="segment.ariaLabel"
          (mouseenter)="active.set(segment.key)"
          (focus)="active.set(segment.key)"
          (blur)="active.set(null)"
        ></button>
      }
    </div>
  `,
})
export class StackedBarComponent {
  readonly segments = input.required<readonly BarSegment[]>();

  readonly active = model<string | null>(null);

  private readonly total = computed(() =>
    this.segments().reduce((sum, segment) => sum + segment.value, 0),
  );

  protected widthOf(segment: BarSegment): number {
    const total = this.total();
    return total > 0 ? (segment.value / total) * 100 : 0;
  }
}
