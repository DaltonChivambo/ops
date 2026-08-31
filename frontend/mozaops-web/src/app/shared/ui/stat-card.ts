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
  /** Quando definido, substitui a formatação numérica (ex.: "95,8%", valores MZN). */
  readonly displayValue?: string;
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
        <div>
          <p class="mb-1.5 text-[0.9375rem] text-gray-600">{{ s.label }}</p>
          <p class="text-[1.75rem] leading-none font-bold">{{ displayValue() }}</p>
        </div>

        <span
          class="inline-flex size-11 items-center justify-center rounded-xl bg-moza-100 text-moza-700"
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

      <p class="flex items-center gap-1.5 text-[0.8125rem]">
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
}
