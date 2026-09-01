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
  /**
   * Unidade em sufixo pequeno e cinzento, à maneira do `app-money`. Fora do
   * número porque é ele que se lê: com "MZN" a negro e no mesmo corpo, o
   * cartão do valor em divergência não cabe a quatro por linha num portátil.
   */
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
      <!-- Rótulo e ícone na mesma linha, o valor sozinho por baixo. O valor
           costumava partilhar a linha com o ícone e ficava com menos 52px —
           num montante de doze dígitos era a diferença entre caber e ser
           cortado. -->
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

      <!-- O corpo desce conforme o número cresce, em vez de o cortar. Cortar um
           montante é pior do que mostrá-lo mais pequeno: "205 641 064,00…" lê-se
           como duzentos milhões quando são duzentos mil milhões.

           Sem title: é justamente por o número nunca ser cortado que o tooltip não
           tinha o que acrescentar — repetia à letra o que já está no ecrã, e
           bastava passar o rato por cima de um cartão para o ver aparecer. -->
      <!-- Tudo colado de propósito: aqui o espaço em branco do template é texto.
           Reflowido, o valor ficava com um espaço à cabeça — que o empurra para a
           direita e o desalinha do rótulo — e outro antes da unidade, a somar ao
           ml-1 que já lhe dá o afastamento. O prettier-ignore tem de ficar
           encostado ao elemento: aplica-se ao nó seguinte, e com um comentário
           pelo meio era o comentário que ele ignorava. -->
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
   * O corpo do valor desce por degraus conforme o número cresce. Nunca se corta
   * um montante: a 1 000 000 000 000,00 MZN (20 caracteres) ainda cabe inteiro
   * num cartão de quatro por linha num portátil.
   *
   * As classes estão escritas por extenso porque o Tailwind lê o código-fonte —
   * uma interpolação do género text-${n} não geraria utilitário nenhum.
   */
  protected readonly valueClass = computed(() => {
    const chars = this.displayValue().length + (this.stat().unit?.length ?? 0);
    const size =
      chars <= 12 ? 'text-2xl' : chars <= 16 ? 'text-xl' : chars <= 21 ? 'text-lg' : 'text-base';
    return `truncate font-display leading-none font-bold tabular-nums ${size}`;
  });
}
