import { ChangeDetectionStrategy, Component, computed, input, model } from '@angular/core';

/** Um segmento da barra. A cor vem em classe porque é sempre uma cor do tema. */
export interface BarSegment {
  /** Identifica o segmento no destaque — o mesmo valor que o `active` toma. */
  readonly key: string;
  readonly label: string;
  readonly value: number;
  /** Classe de fundo, ex.: `bg-emerald-500`. */
  readonly className: string;
  /** Já formatado por quem sabe as unidades: o gráfico não conhece moedas. */
  readonly ariaLabel: string;
}

/**
 * Barra empilhada de proporções, com destaque.
 *
 * O `active` é bidireccional de propósito: quem a usa costuma ter uma tabela ao
 * lado com as mesmas linhas, e apontar a um segmento tem de acender a linha —
 * e a linha, o segmento. Sem isso seriam dois destaques que se ignoram.
 *
 * Duas decisões que aqui parecem detalhe e não são:
 *
 * A largura mínima existe porque as fatias que interessam são fracções de ponto
 * percentual: sem ela a barra saía de uma cor só e não dizia nada.
 *
 * Quem arredonda as pontas é o contentor, e os segmentos ficam rectos. A
 * arredondar nos dois sítios, um segmento de 10px levava um raio maior do que
 * ele próprio e saía cortado contra o canto.
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

  /** Segmento em destaque, partilhado com quem estiver ao lado. */
  readonly active = model<string | null>(null);

  private readonly total = computed(() =>
    this.segments().reduce((sum, segment) => sum + segment.value, 0),
  );

  protected widthOf(segment: BarSegment): number {
    const total = this.total();
    return total > 0 ? (segment.value / total) * 100 : 0;
  }
}
