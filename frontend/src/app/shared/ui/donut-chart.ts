import { ChangeDetectionStrategy, Component, computed, input, signal } from '@angular/core';

import { numberFormatter } from '../format';

/**
 * Geometria do anel. Traço fino de propósito: quase 90% deste anel é uma cor só,
 * e a 18px de espessura essa mancha pesava o cartão todo. A 12 o anel lê-se como
 * uma linha e o miolo fica para o número, que é o que se vem cá ver.
 */
const SIZE = 200;
const RADIUS = 84;
const STROKE = 12;
/** Ao destacar, o arco engorda para dentro e para fora — daí a folga no viewBox. */
const STROKE_ACTIVE = 18;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;
/** Intervalo entre fatias, em comprimento de arco (equivale a 4°). */
const GAP = (4 / 360) * CIRCUMFERENCE;
/** Uma fatia de 0,7% não pode desaparecer: abaixo disto lê-se como um traço. */
const MIN_DASH = 3;

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

/** Uma fatia do anel: o rótulo por extenso, o curto para o centro, e a contagem. */
export interface DonutSlice {
  /** Nome por extenso, para a legenda. */
  readonly name: string;
  /** Versão curta, que cabe no miolo do anel ao destacar a fatia. */
  readonly short: string;
  readonly count: number;
  /** Cor em hexadecimal: entra em SVG e em drop-shadow, onde classes não servem. */
  readonly color: string;
}

interface Arc extends DonutSlice {
  readonly dash: number;
  readonly offset: number;
  readonly share: number;
}

/**
 * Anel de proporções — SVG à mão, sem biblioteca de gráficos.
 *
 * Sabe desenhar fatias e mais nada: quem o usa dá-lhe a lista e as palavras.
 * Estava colado aos fechos por tratar, e o que era desse assunto eram três
 * linhas de mapeamento no meio de duzentas de geometria e de interacção.
 *
 * Apontar a uma fatia (ou à linha da legenda) destaca-a e troca o centro pela
 * leitura dessa fatia. A legenda são botões e não itens de lista mortos: é o
 * que dá o mesmo destaque a quem navega por teclado.
 */
@Component({
  selector: 'app-donut-chart',
  changeDetection: ChangeDetectionStrategy.OnPush,
  // O cartão que o recebe é flex em coluna; sem isto o anel não esticava.
  host: { class: 'flex flex-1' },
  template: `
    <div class="flex flex-1 flex-col items-center justify-center gap-6 @md:flex-row @md:gap-10">
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
                class="text-gray-100/80"
                [attr.stroke-width]="stroke"
                stroke-linecap="round"
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
                  [attr.opacity]="active() && !on ? 0.22 : 1"
                  class="cursor-pointer transition-[stroke-width,opacity,filter] duration-200"
                  [style.filter]="on ? 'drop-shadow(0 2px 6px ' + arc.color + '59)' : null"
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
          <span
            class="font-display text-[2.5rem] leading-none font-bold tracking-tight tabular-nums text-gray-900"
          >
            {{ count(focus ? focus.count : total()) }}
          </span>
          @if (focus) {
            <span
              class="mt-1.5 rounded-full px-2 py-0.5 text-2xs font-bold tabular-nums text-white"
              [style.backgroundColor]="focus.color"
            >
              {{ share(focus.share) }}
            </span>
            <span class="mt-1 text-2xs leading-tight text-gray-500">{{ focus.short }}</span>
          } @else {
            <span class="mt-1.5 text-2xs tracking-[0.18em] text-gray-400 uppercase">
              {{ caption() }}
            </span>
          }
        </div>
      </div>

      <ul class="flex w-full max-w-sm flex-col gap-1">
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
          <li class="text-center text-sm text-gray-400">{{ emptyMessage() }}</li>
        }
      </ul>
    </div>
  `,
})
export class DonutChartComponent {
  readonly slices = input.required<readonly DonutSlice[]>();
  /** A palavra debaixo do total, quando não há fatia destacada — ex.: «por tratar». */
  readonly caption = input.required<string>();
  /** O que dizer quando não há nada para mostrar. */
  readonly emptyMessage = input('Sem dados.');
  /** O anel é uma imagem para quem não o vê: isto abre a frase que o descreve. */
  readonly ariaPrefix = input.required<string>();

  protected readonly size = SIZE;
  protected readonly radius = RADIUS;
  protected readonly stroke = STROKE;
  protected readonly strokeActive = STROKE_ACTIVE;
  protected readonly circumference = CIRCUMFERENCE;

  /** Fatia em destaque — pelo rato no anel, ou pelo rato/teclado na legenda. */
  protected readonly active = signal<string | null>(null);

  private readonly segments = computed(() => this.slices().filter((slice) => slice.count > 0));

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
      const dash = Math.max(arcLength - gap - STROKE, MIN_DASH);
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
    return `${this.ariaPrefix()}, ${this.count(this.total())} no total. ${parts.join('. ')}.`;
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
