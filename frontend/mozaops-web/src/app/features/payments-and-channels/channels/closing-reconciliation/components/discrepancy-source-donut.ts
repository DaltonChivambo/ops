import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

import { numberFormatter } from '../../../../../shared/format';
import { CardComponent } from '../../../../../shared/ui/card';
import type { ClosingSummary } from '../data/models';

/** Geometria do anel — os mesmos raios que o Recharts recebia no v1. */
const SIZE = 200;
const INNER_RADIUS = 72;
const OUTER_RADIUS = 92;
const RADIUS = (INNER_RADIUS + OUTER_RADIUS) / 2; // 82
const STROKE = OUTER_RADIUS - INNER_RADIUS; // 20
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;
/** `paddingAngle={3}` do v1, convertido para comprimento de arco. */
const GAP = (3 / 360) * CIRCUMFERENCE;

interface Segment {
  readonly name: string;
  readonly count: number;
  readonly color: string;
}

interface Arc extends Segment {
  readonly dash: number;
  readonly offset: number;
}

/**
 * Fechos por tratar, em anel — SVG à mão, sem biblioteca de gráficos.
 * Os duplicados entram apesar de não serem divergência: ninguém sabe se a
 * chave confere enquanto a duplicação não se desfizer, e é trabalho igual.
 */
@Component({
  selector: 'app-discrepancy-source-donut',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CardComponent],
  template: `
    <section appCard class="flex flex-col gap-4">
      <h2 class="text-lg font-bold">Fechos por Tratar</h2>

      <!-- Abaixo do xl este cartão ocupa a largura toda, e o anel sozinho ao meio
           deixava-o um caixote vazio. Aí anel e legenda ficam lado a lado; na
           coluna estreita do xl voltam a empilhar. -->
      <div
        class="flex flex-col items-center gap-5 sm:flex-row sm:justify-center sm:gap-10 xl:flex-col xl:gap-4"
      >
      <div class="relative aspect-square w-full max-w-[13rem] min-w-[9rem] shrink-0">
        @if (segments().length > 0) {
          <svg
            class="h-full w-full"
            [attr.viewBox]="'0 0 ' + size + ' ' + size"
            aria-hidden="true"
          >
            <!-- rotate(-90) põe o início ao meio-dia, como o startAngle={90}. -->
            <g [attr.transform]="'rotate(-90 ' + size / 2 + ' ' + size / 2 + ')'">
              @for (arc of arcs(); track arc.name) {
                <circle
                  [attr.cx]="size / 2"
                  [attr.cy]="size / 2"
                  [attr.r]="radius"
                  fill="none"
                  [attr.stroke]="arc.color"
                  [attr.stroke-width]="stroke"
                  stroke-linecap="round"
                  [attr.stroke-dasharray]="arc.dash + ' ' + circumference"
                  [attr.stroke-dashoffset]="arc.offset"
                />
              }
            </g>
          </svg>
        } @else {
          <div
            class="absolute inset-4 rounded-full border-[1.35rem] border-emerald-100"
            aria-hidden="true"
          ></div>
        }

        <div
          class="pointer-events-none absolute inset-0 flex flex-col items-center justify-center"
        >
          <span class="font-display text-3xl leading-tight font-bold tabular-nums">{{
            count(total())
          }}</span>
          <span class="text-2xs tracking-widest text-gray-600 uppercase">Fechos</span>
        </div>
      </div>

      <ul class="flex w-full max-w-sm flex-col gap-2.5 xl:max-w-none">
        @for (segment of segments(); track segment.name) {
          <li class="flex items-center gap-2 text-sm">
            <span
              class="size-2 shrink-0 rounded-full"
              [style.backgroundColor]="segment.color"
              aria-hidden="true"
            ></span>
            <span class="font-semibold">{{ segment.name }}</span>
            <span class="ml-auto text-gray-400">{{ count(segment.count) }}</span>
          </li>
        } @empty {
          <li class="text-center text-sm text-gray-400">Todos os fechos conferem.</li>
        }
      </ul>
      </div>
    </section>
  `,
})
export class DiscrepancySourceDonutComponent {
  readonly summary = input.required<ClosingSummary>();

  protected readonly size = SIZE;
  protected readonly radius = RADIUS;
  protected readonly stroke = STROKE;
  protected readonly circumference = CIRCUMFERENCE;

  protected readonly segments = computed<readonly Segment[]>(() => {
    const s = this.summary();
    return [
      { name: 'Não creditado', count: s.missingCount, color: '#57617a' },
      { name: 'Creditado incorrectamente', count: s.mismatchCount, color: '#e8342a' },
      { name: 'Períodos duplicados', count: s.duplicatedPeriods, color: '#fe9a00' },
    ].filter((segment) => segment.count > 0);
  });

  protected readonly total = computed(() =>
    this.segments().reduce((sum, segment) => sum + segment.count, 0),
  );

  protected readonly arcs = computed<readonly Arc[]>(() => {
    const segments = this.segments();
    const total = this.total();
    if (total === 0) return [];

    // Uma fatia sozinha não tem vizinha de quem se separar: sem isto ficava com
    // um golpe de 3° a meio de um anel que devia ser contínuo.
    const gap = segments.length > 1 ? GAP : 0;

    let cursor = 0;
    return segments.map((segment) => {
      const arcLength = (segment.count / total) * CIRCUMFERENCE;
      // A ponta redonda acrescenta metade da espessura de cada lado.
      const dash = Math.max(arcLength - gap - STROKE, 0.1);
      const offset = -(cursor + gap / 2 + STROKE / 2);
      cursor += arcLength;
      return { ...segment, dash, offset };
    });
  });

  protected count = (value: number) => numberFormatter.format(value);
}
