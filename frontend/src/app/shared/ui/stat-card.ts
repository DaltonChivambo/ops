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
  // Ocupa a célula inteira: uma nota em duas linhas não pode deixar um cartão
  // mais alto que os vizinhos.
  host: { class: 'block h-full' },
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

    <section appCard compact class="@container flex h-full flex-col gap-2 2xl:gap-2.5">
      <div class="flex items-center justify-between gap-2">
        <p class="min-w-0 truncate text-sm text-gray-600 2xl:text-[0.9375rem]">{{ s.label }}</p>

        <span
          class="inline-flex size-9 shrink-0 items-center justify-center rounded-lg bg-moza-100 text-moza-700 2xl:size-10"
        >
          @switch (s.icon) {
            @case ('file-check') {
              <svg lucideFileCheckCorner [size]="18" [strokeWidth]="1.8" class="2xl:size-5"></svg>
            }
            @case ('percent') {
              <svg lucidePercent [size]="18" [strokeWidth]="1.8" class="2xl:size-5"></svg>
            }
            @case ('banknote') {
              <svg lucideBanknote [size]="18" [strokeWidth]="1.8" class="2xl:size-5"></svg>
            }
            @case ('alert-triangle') {
              <svg lucideTriangleAlert [size]="18" [strokeWidth]="1.8" class="2xl:size-5"></svg>
            }
          }
        </span>
      </div>

      <!-- O corpo encolhe até caber na largura do cartão, em vez de o cortar:
           cortar um montante lê-se como outro montante.
           Tudo colado: aqui o espaço em branco do template é texto. -->
      <!-- prettier-ignore -->
      <p
        class="font-display leading-none font-bold whitespace-nowrap tabular-nums text-[length:min(1.25rem,var(--fit))] 2xl:text-[length:min(1.375rem,var(--fit))]"
        [style.--fit]="fit()"
      >{{ displayValue()
      }}@if (s.unit) {<span class="ml-1 text-[0.55em] font-normal text-gray-400">{{ s.unit }}</span>}</p>

      <p class="mt-auto flex items-center gap-1.5 text-[0.8125rem] 2xl:text-sm">
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
   * O tamanho que faz o número caber na largura do cartão (`100cqi`). Conta-se
   * o texto em larguras de letra, medidas na fonte do número: dígito 0,645em,
   * espaço dos milhares e vírgula 0,27em, o resto (o `%`) até 0,95em, e a
   * unidade com a margem 1,5em. Mais 4% de folga. O CSS fica com o menor entre
   * isto e o tamanho máximo.
   */
  protected readonly fit = computed(() => {
    const glyph = (ch: string) => (/\d/.test(ch) ? 0.645 : /[\s,.]/.test(ch) ? 0.27 : 0.95);
    const text = [...this.displayValue()].reduce((sum, ch) => sum + glyph(ch), 0);
    const unit = this.stat().unit ? 1.5 : 0;
    return `calc(100cqi / ${((text + unit) * 1.04).toFixed(3)})`;
  });
}
