import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

import { formatAmount, numberFormatter } from '../../../../../shared/format';
import { type Stat, StatCardComponent } from '../../../../../shared/ui/stat-card';
import type { ValidationResult } from '../data/models';

/** Cada cartão leva a sua própria leitura por baixo, em vez do intervalo repetido. */
interface StatWithNote {
  readonly stat: Stat;
  readonly note: string;
}

/**
 * Os quatro indicadores da execução. O contexto (período, relatório, quando
 * correu) fica na `app-execution-bar`, acima — aqui é só o apuramento.
 */
@Component({
  selector: 'app-result-stats',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [StatCardComponent],
  template: `
    <!-- Quatro por linha só quando sobram ~1024px de conteúdo, que é onde cada
         cartão fica com uns 240px e o rótulo deixa de truncar. Esses 1024px
         chegam a janelas diferentes conforme a barra lateral:
           encolhida  -> largura - 76 - 64  = precisa de 1170px de janela
           aberta     -> largura - 264 - 64 = precisa de 1360px
         Daí as duas regras. Sem a segunda, abrir a barra a 1280px espremia os
         quatro cartões para 226px e voltava a cortar os montantes. -->
    <div
      class="grid grid-cols-2 gap-4 min-[1360px]:grid-cols-4 min-[1170px]:group-data-[sidebar=collapsed]/shell:grid-cols-4"
    >
      @for (item of stats(); track item.stat.id) {
        <app-stat-card [stat]="item.stat" [periodLabel]="item.note" />
      }
    </div>
  `,
})
export class ResultStatsComponent {
  readonly result = input.required<ValidationResult>();

  protected readonly stats = computed<readonly StatWithNote[]>(() => {
    const s = this.result().summary;
    const n = (value: number) => numberFormatter.format(value);

    return [
      {
        stat: {
          id: 'processed',
          label: 'Fechos Processados',
          value: s.processed,
          icon: 'file-check',
        },
        note: `${n(s.divergent)} com divergência`,
      },
      {
        stat: {
          id: 'rate',
          label: 'Taxa de Validação',
          value: s.validationRate,
          displayValue: `${n(s.validationRate)}%`,
          icon: 'percent',
        },
        note: `${n(s.matched)} fechos conferem`,
      },
      {
        stat: {
          id: 'divergence',
          label: 'Valor em Divergência',
          value: s.divergenceAmount,
          displayValue: formatAmount(s.divergenceAmount),
          unit: 'MZN',
          icon: 'banknote',
        },
        note: `${n(s.missingCount)} não creditados · ${n(s.mismatchCount)} incorrectos`,
      },
      {
        stat: {
          id: 'cases',
          label: 'Casos Pendentes',
          value: s.openCases,
          icon: 'alert-triangle',
        },
        note: `${n(s.resolvedCases)} já regularizados`,
      },
    ];
  });
}
