import { ChangeDetectionStrategy, Component, computed, input, signal } from '@angular/core';

import { numberFormatter } from '../../../../../shared/format';
import { CardComponent } from '../../../../../shared/ui/card';
import type { ClosingSummary } from '../data/models';

/** Geometria do anel. */
const SIZE = 200;
const RADIUS = 82;
const STROKE = 18;
/** Ao destacar, o arco engorda para dentro e para fora — daí a folga no viewBox. */
const STROKE_ACTIVE = 26;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;
/** Intervalo entre fatias, em comprimento de arco (equivale a 3°). */
const GAP = (3 / 360) * CIRCUMFERENCE;

interface Segment {
  readonly name: string;
  readonly short: string;
  readonly count: number;
  readonly color: string;
}

interface Arc extends Segment {
  readonly dash: number;
  readonly offset: number;
  readonly share: number;
}

/**
 * Fechos por tratar, em anel — SVG à mão, sem biblioteca de gráficos.
 * Os duplicados entram apesar de não serem divergência: ninguém sabe se a
 * chave confere enquanto a duplicação não se desfizer, e é trabalho igual.
 *
 * Apontar a uma fatia (ou à linha da legenda) destaca-a e troca o centro pela
 * leitura dessa fatia. A legenda são botões e não itens de lista mortos: é o
 * que dá o mesmo destaque a quem navega por teclado.
 */
@Component({
  selector: 'app-discrepancy-source-donut',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CardComponent],
  // O anfitrião estica na grelha (os itens de grid esticam por omissão), mas o
  // section lá dentro ficava na altura do conteúdo — era isso que deixava este
  // cartão e o dos montantes com alturas diferentes.
  host: { class: 'block h-full' },
  template: `
    <section appCard class="flex h-full flex-col gap-4">
      <h2 class="text-lg font-bold">Fechos por Tratar</h2>

      <!-- Abaixo do xl este cartão ocupa a largura toda, e o anel sozinho ao meio
           deixava-o um caixote vazio. Aí anel e legenda ficam lado a lado; na
           coluna estreita do xl voltam a empilhar. -->
      <div
        class="flex flex-1 flex-col items-center justify-center gap-5 sm:flex-row sm:gap-10 xl:flex-col xl:gap-6"
      >
        <div class="relative aspect-square w-full max-w-[13rem] min-w-[9rem] shrink-0">
          @if (arcs().length > 0) {
            <svg
              class="h-full w-full overflow-visible motion-safe:animate-[donut-in_520ms_cubic-bezier(0.16,1,0.3,1)]"
              [attr.viewBox]="'0 0 ' + size + ' ' + size"
              role="img"
              [attr.aria-label]="ariaSummary()"
              (mouseleave)="active.set(null)"
            >
              <!-- rotate(-90) põe o início ao meio-dia. -->
              <g [attr.transform]="'rotate(-90 ' + size / 2 + ' ' + size / 2 + ')'">
                <!-- Sulco por baixo: sem ele, um anel quase todo de uma cor não se
                     percebe como parte de um todo. -->
                <circle
                  [attr.cx]="size / 2"
                  [attr.cy]="size / 2"
                  [attr.r]="radius"
                  fill="none"
                  stroke="currentColor"
                  class="text-gray-100"
                  [attr.stroke-width]="stroke"
                />

                @for (arc of arcs(); track arc.name) {
                  @let on = active() === arc.name;
                  <circle
                    [attr.cx]="size / 2"
                    [attr.cy]="size / 2"
                    [attr.r]="radius"
                    fill="none"
                    [attr.stroke]="arc.color"
                    [attr.stroke-width]="on ? strokeActive : stroke"
                    stroke-linecap="round"
                    [attr.stroke-dasharray]="arc.dash + ' ' + circumference"
                    [attr.stroke-dashoffset]="arc.offset"
                    [attr.opacity]="active() && !on ? 0.28 : 1"
                    class="cursor-pointer transition-[stroke-width,opacity] duration-200"
                    (mouseenter)="active.set(arc.name)"
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
            class="pointer-events-none absolute inset-0 flex flex-col items-center justify-center px-6 text-center"
          >
            @let focus = activeArc();
            <span class="font-display text-3xl leading-tight font-bold tabular-nums">
              {{ count(focus ? focus.count : total()) }}
            </span>
            @if (focus) {
              <span class="mt-0.5 text-sm font-semibold tabular-nums" [style.color]="focus.color">
                {{ share(focus.share) }}
              </span>
              <span class="mt-0.5 text-2xs leading-tight text-gray-500">{{ focus.short }}</span>
            } @else {
              <span class="text-2xs tracking-widest text-gray-600 uppercase">Fechos</span>
            }
          </div>
        </div>

        <ul class="flex w-full max-w-sm flex-col gap-1 xl:max-w-none">
          @for (arc of arcs(); track arc.name) {
            @let on = active() === arc.name;
            <li>
              <button
                type="button"
                class="flex w-full items-center gap-2.5 rounded-lg px-2 py-1.5 text-left text-sm transition-colors hover:bg-gray-50 focus-visible:bg-gray-50 focus-visible:outline-none"
                (mouseenter)="active.set(arc.name)"
                (mouseleave)="active.set(null)"
                (focus)="active.set(arc.name)"
                (blur)="active.set(null)"
              >
                <span
                  class="size-2.5 shrink-0 rounded-full transition-transform"
                  [class.scale-125]="on"
                  [style.backgroundColor]="arc.color"
                  aria-hidden="true"
                ></span>
                <span class="min-w-0 flex-1 truncate" [class.font-semibold]="on">
                  {{ arc.name }}
                </span>
                <span class="shrink-0 text-2xs tabular-nums text-gray-400">
                  {{ share(arc.share) }}
                </span>
                <span class="w-10 shrink-0 text-right font-semibold tabular-nums">
                  {{ count(arc.count) }}
                </span>
              </button>
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
  protected readonly strokeActive = STROKE_ACTIVE;
  protected readonly circumference = CIRCUMFERENCE;

  /** Fatia em destaque — pelo rato no anel, ou pelo rato/teclado na legenda. */
  protected readonly active = signal<string | null>(null);

  private readonly segments = computed<readonly Segment[]>(() => {
    const s = this.summary();
    return [
      { name: 'Não creditado', short: 'não creditados', count: s.missingCount, color: '#57617a' },
      {
        name: 'Creditado incorrectamente',
        short: 'creditados a mais ou a menos',
        count: s.mismatchCount,
        color: '#e8342a',
      },
      {
        name: 'Períodos duplicados',
        short: 'em períodos duplicados',
        count: s.duplicatedPeriods,
        color: '#fe9a00',
      },
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
      return { ...segment, dash, offset, share: segment.count / total };
    });
  });

  protected readonly activeArc = computed(
    () => this.arcs().find((arc) => arc.name === this.active()) ?? null,
  );

  /** O anel é uma imagem para quem não o vê; o texto tem de valer por ele. */
  protected readonly ariaSummary = computed(() => {
    const parts = this.arcs().map(
      (arc) => `${arc.name}: ${this.count(arc.count)} (${this.share(arc.share)})`,
    );
    return `Fechos por tratar, ${this.count(this.total())} no total. ${parts.join('. ')}.`;
  });

  protected count = (value: number) => numberFormatter.format(value);

  /** Sem casas decimais até 10%, uma abaixo disso: "1" e "0,7" dizem coisas diferentes. */
  protected share(value: number): string {
    const percent = value * 100;
    return `${percent.toLocaleString('pt-PT', {
      minimumFractionDigits: percent < 10 ? 1 : 0,
      maximumFractionDigits: percent < 10 ? 1 : 0,
    })}%`;
  }
}
