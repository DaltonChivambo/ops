import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import {
  LucideArrowDown,
  LucideArrowUp,
  LucideBanknote,
  LucideFileCheckCorner,
  LucidePercent,
  LucideTriangleAlert,
} from '@lucide/angular';

import { numberFormatter } from '../format';
import { CardComponent } from './card';

/** Um indicador do cabeçalho de resultado — só os quatro ícones que estão em uso. */
export interface Stat {
  readonly id: string;
  readonly label: string;
  readonly value: number;
  /** Quando definido, substitui a formatação numérica (ex.: "95,8%"). */
  readonly displayValue?: string;
  /** Unidade em sufixo pequeno e cinzento, fora do número: é ele que se lê. */
  readonly unit?: string;
  /** Variação vs. período anterior; omitir quando não há comparativo. */
  readonly changePercent?: number;
  readonly icon: 'file-check' | 'percent' | 'banknote' | 'alert-triangle';
}

/** `@switch` e não mapa nome→componente: cada ícone do Lucide é um selector de atributo, não indexável. */
@Component({
  selector: 'app-stat-card',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CardComponent,
    LucideArrowDown,
    LucideArrowUp,
    LucideBanknote,
    LucideFileCheckCorner,
    LucidePercent,
    LucideTriangleAlert,
  ],
  template: `
    @let s = stat();

    <section appCard class="flex flex-col gap-3">
      <div class="flex items-start justify-between gap-2">
        <p class="min-w-0 truncate text-base text-gray-600">{{ s.label }}</p>

        <span
          class="inline-flex size-11 shrink-0 items-center justify-center rounded-xl bg-moza-100 text-moza-700"
        >
          @switch (s.icon) {
            @case ('file-check') {
              <svg lucideFileCheckCorner [size]="20" [strokeWidth]="1.8"></svg>
            }
            @case ('percent') {
              <svg lucidePercent [size]="20" [strokeWidth]="1.8"></svg>
            }
            @case ('banknote') {
              <svg lucideBanknote [size]="20" [strokeWidth]="1.8"></svg>
            }
            @case ('alert-triangle') {
              <svg lucideTriangleAlert [size]="20" [strokeWidth]="1.8"></svg>
            }
          }
        </span>
      </div>

      <!-- O corpo desce conforme o número cresce, em vez de o cortar: cortar um
           montante lê-se como outro montante.
           Tudo colado: aqui o espaço em branco do template é texto. -->
      <!-- prettier-ignore -->
      <p [class]="valueClass()">{{ displayValue()
      }}@if (s.unit) {<span class="ml-1 text-[0.55em] font-normal text-gray-400">{{ s.unit }}</span>}</p>

      <p class="flex items-center gap-1.5 text-sm">
        @if (s.changePercent !== undefined) {
          <span
            class="inline-flex items-center gap-0.5 font-semibold"
            [class]="isPositive() ? 'text-emerald-600' : 'text-alert-500'"
          >
            @if (isPositive()) {
              <svg lucideArrowUp [size]="14" [strokeWidth]="2.2"></svg>
            } @else {
              <svg lucideArrowDown [size]="14" [strokeWidth]="2.2"></svg>
            }
            {{ isPositive() ? '+' : '' }}{{ s.changePercent.toFixed(1) }}%
          </span>
        }
        <span class="text-gray-400">{{ periodLabel() }}</span>
      </p>
    </section>
  `,
})
export class StatCardComponent {
  readonly stat = input.required<Stat>();
  readonly periodLabel = input.required<string>();

  protected readonly isPositive = computed(() => (this.stat().changePercent ?? 0) >= 0);

  protected readonly displayValue = computed(() => {
    const s = this.stat();
    return s.displayValue ?? numberFormatter.format(s.value);
  });

  /**
   * O corpo desce por degraus: a 1 000 000 000 000,00 MZN ainda cabe inteiro a
   * quatro cartões por linha. As classes vão por extenso porque o Tailwind lê o
   * código-fonte e não geraria nada a partir de uma interpolação.
   */
  protected readonly valueClass = computed(() => {
    const chars = this.displayValue().length + (this.stat().unit?.length ?? 0);
    const size =
      chars <= 12 ? 'text-2xl' : chars <= 16 ? 'text-xl' : chars <= 21 ? 'text-lg' : 'text-base';
    return `truncate font-display leading-none font-bold tabular-nums ${size}`;
  });
}
