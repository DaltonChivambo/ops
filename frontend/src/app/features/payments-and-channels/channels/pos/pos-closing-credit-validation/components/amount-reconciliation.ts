import { ChangeDetectionStrategy, Component, computed, input, output, signal } from '@angular/core';
import { LucideCopyCheck, LucideCopyX, LucideLoaderCircle } from '@lucide/angular';

import {
  formatAmount,
  formatMzn,
  formatSignedAmount,
  formatSignedMzn,
  numberFormatter,
  percentageShares,
} from '../../../../../../shared/format';
import { CollapsibleCardComponent } from '../../../../../../shared/ui/collapsible-card';
import { InfoTooltipComponent } from '../../../../../../shared/ui/info-tooltip';
import { StackedBarComponent, type BarSegment } from '../../../../../../shared/ui/stacked-bar';
import type { ClosingSummary } from '../data/models';

interface Row {
  readonly key: string;
  readonly label: string;
  readonly count: number;
  readonly simo: number;
  readonly banka: number;
  readonly barClass: string;
  readonly dotClass: string;
  /** Uma frase a explicar o estado — o "i" ao lado do rótulo só aparece com isto. */
  readonly description?: string;
}

type Source = 'simo' | 'banka' | 'difference';

/**
 * Reconciliação de montantes — não quantos fechos divergem, mas quanto dinheiro
 * está em cada estado.
 *
 * Os fechos repetidos da SIMO não entram aqui: o montante deles é o do fecho
 * original, que já está na linha do seu estado, e uma linha própria punha os
 * dois lados a somar duas vezes o mesmo dinheiro. Vivem na faixa por cima
 * (`app-simo-repeated-lines`) e, com valor, no relatório.
 */
@Component({
  selector: 'app-amount-reconciliation',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CollapsibleCardComponent, InfoTooltipComponent, StackedBarComponent],
  template: `
    <app-collapsible-card heading="Reconciliação de Montantes" storageKey="reconciliacao-montantes">
      <p cardAside class="text-xs text-gray-400">Apurado na SIMO vs creditado no Banka · MZN</p>

      <div class="flex flex-col gap-2">
        <!-- Interruptor simples: a barra e a legenda por baixo dela mudam de lado
             consoante o que se escolhe — o resto (a tabela) já mostra os dois. -->
        <div
          role="tablist"
          aria-label="Lado da barra"
          class="ml-auto inline-flex gap-1 rounded-lg bg-moza-100 p-0.5"
        >
          @for (option of sources; track option) {
            <button
              type="button"
              role="tab"
              [attr.aria-selected]="source() === option"
              (click)="source.set(option)"
              class="rounded-md px-2.5 py-1 text-2xs font-bold transition-colors"
              [class]="
                source() === option
                  ? 'bg-white text-moza-800 shadow-sm'
                  : 'text-moza-500 hover:text-moza-800'
              "
            >
              {{ sourceLabel(option) }}
            </button>
          }
        </div>

        <app-stacked-bar [segments]="barSegments()" [(active)]="active" />

        <!-- Reserva a altura sempre, para a barra não saltar quando isto aparece. -->
        <p class="flex min-h-4 items-center gap-2 text-xs">
          @if (activeRow(); as row) {
            <span class="size-2 shrink-0 rounded-full" [class]="row.dotClass"></span>
            <span class="font-semibold text-gray-900">{{ row.label }}</span>
            <span class="text-gray-400">{{ share(row) }} {{ sourceCaption() }}</span>
            <span class="ml-auto font-semibold whitespace-nowrap tabular-nums text-gray-900">
              {{ displayAmount(row) }} <span class="font-normal text-gray-400">MZN</span>
            </span>
          }
        </p>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full min-w-xl border-collapse text-sm">
          <thead>
            <tr class="border-b border-gray-100 text-gray-400">
              <th scope="col" [class]="th + ' py-2 pr-3 pl-1.5 text-left'">Validação</th>
              <th scope="col" [class]="th + ' px-4 py-2 text-right'">Fechos</th>
              <th scope="col" [class]="th + ' px-4 py-2 text-right'">Montante SIMO</th>
              <th scope="col" [class]="th + ' px-4 py-2 text-right'">Montante Banka</th>
              <th scope="col" [class]="th + ' py-2 pr-1.5 pl-3 text-right'">Diferença</th>
            </tr>
          </thead>
          <tbody>
            @for (row of rows(); track row.key) {
              @let difference = row.banka - row.simo;
              @let on = active() === row.key;

              <tr
                class="border-b border-gray-100 text-gray-600 transition-colors"
                [class.bg-gray-50]="on"
                (mouseenter)="active.set(row.key)"
                (mouseleave)="active.set(null)"
              >
                <td class="py-3 pr-3 pl-1.5">
                  <span class="flex items-center gap-2">
                    <span
                      class="size-2 shrink-0 rounded-full transition-transform"
                      [class]="row.dotClass"
                      [class.scale-125]="on"
                      aria-hidden="true"
                    ></span>
                    <span class="font-semibold text-gray-900">{{ row.label }}</span>
                    @if (row.description) {
                      <app-info-tooltip [text]="row.description" [label]="'Sobre ' + row.label" />
                    }
                  </span>
                </td>
                <td class="px-4 py-3 text-right whitespace-nowrap tabular-nums">
                  {{ count(row.count) }}
                </td>
                <td class="px-4 py-3 text-right whitespace-nowrap tabular-nums">
                  {{ amount(row.simo) }}
                </td>
                <td class="px-4 py-3 text-right whitespace-nowrap tabular-nums">
                  {{ row.key === 'missing' ? '—' : amount(row.banka) }}
                </td>
                <td
                  class="py-3 pr-1.5 pl-3 text-right whitespace-nowrap tabular-nums"
                  [class.font-semibold]="difference !== 0"
                  [class.text-alert-600]="difference !== 0"
                >
                  {{ difference === 0 ? '—' : signedAmount(difference) }}
                </td>
              </tr>
            }

            <tr class="font-semibold text-gray-900">
              <td class="py-3 pr-3 pl-1.5">
                <span class="inline-flex items-center gap-2">
                  Total
                  <app-info-tooltip [text]="totalDescription" label="Sobre o total" />
                </span>
              </td>
              <td class="px-4 py-3 text-right whitespace-nowrap tabular-nums">
                {{ count(summary().processed) }}
              </td>
              <td class="px-4 py-3 text-right whitespace-nowrap tabular-nums">
                {{ amount(totalSimo()) }}
              </td>
              <td class="px-4 py-3 text-right whitespace-nowrap tabular-nums">
                {{ amount(totalBanka()) }}
              </td>
              <td class="py-3 pr-1.5 pl-3 text-right whitespace-nowrap tabular-nums text-alert-600">
                {{ signedAmount(totalBanka() - totalSimo()) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </app-collapsible-card>
  `,
})
export class AmountReconciliationComponent {
  readonly summary = input.required<ClosingSummary>();
  protected readonly th = 'text-2xs font-semibold tracking-wider uppercase';

  /** Estado em destaque — vindo da barra ou da linha da tabela, indiferentemente. */
  protected readonly active = signal<string | null>(null);

  /** De que lado a barra desenha as proporções — a tabela mostra sempre os dois. */
  protected readonly sources: readonly Source[] = ['simo', 'banka', 'difference'];
  protected readonly source = signal<Source>('simo');

  protected sourceLabel(option: Source): string {
    switch (option) {
      case 'simo':
        return 'SIMO';
      case 'banka':
        return 'Banka';
      case 'difference':
        return 'Diferença';
    }
  }

  protected readonly sourceCaption = computed(() => {
    switch (this.source()) {
      case 'simo':
        return 'do apurado na SIMO';
      case 'banka':
        return 'do creditado no Banka';
      case 'difference':
        return 'da diferença total entre SIMO e Banka';
    }
  });

  protected readonly rows = computed<readonly Row[]>(() => {
    const s = this.summary();
    return [
      {
        key: 'match',
        label: 'Crédito confere',
        count: s.matched,
        simo: s.simoAmountMatched,
        banka: s.bankaAmountMatched,
        barClass: 'bg-emerald-500',
        dotClass: 'bg-emerald-500',
        description: 'Fechos cujo crédito no Banka corresponde ao valor apurado na SIMO.',
      },
      {
        key: 'mismatch',
        label: 'Creditado incorrectamente',
        count: s.mismatchCount,
        simo: s.simoAmountMismatched,
        banka: s.bankaAmountMismatched,
        barClass: 'bg-alert-500',
        dotClass: 'bg-alert-500',
        description: 'Fechos creditados no Banka, mas com valor diferente do apurado na SIMO.',
      },
      {
        key: 'missing',
        label: 'Não creditado',
        count: s.missingCount,
        simo: s.simoAmountMissing,
        banka: 0,
        barClass: 'bg-moza-500',
        dotClass: 'bg-moza-500',
        description: 'Fechos apurados na SIMO, mas sem crédito correspondente no Banka.',
      },
      // Banka duplica tal como a SIMO aqui; dar o lado por zero punha esse dinheiro como em falta.
      {
        key: 'duplicated',
        label: 'Períodos repetidos',
        count: s.duplicatedPeriods,
        simo: s.simoAmountDuplicated,
        banka: s.bankaAmountDuplicated,
        barClass: 'bg-amber-500',
        dotClass: 'bg-amber-500',
        description:
          'Fechos com períodos repetidos: o mesmo POS e período aparece mais do que uma vez, na SIMO ou no Banka.',
      },
    ];
  });

  /**
   * O valor do lado escolhido no interruptor. Na diferença é o absoluto — a
   * barra é proporções, e um estado a dever (Banka abaixo da SIMO) não pode
   * "descontar" largura a outro que sobra; `displayAmount` é que mostra o
   * sinal, esse sim.
   */
  protected valueOf(row: Row): number {
    switch (this.source()) {
      case 'simo':
        return row.simo;
      case 'banka':
        return row.banka;
      case 'difference':
        return Math.abs(row.banka - row.simo);
    }
  }

  /** O que se lê ao lado da barra — na diferença, com sinal, o resto sem. */
  protected displayAmount(row: Row): string {
    return this.source() === 'difference'
      ? this.signedAmount(row.banka - row.simo)
      : this.amount(this.valueOf(row));
  }

  /**
   * Os segmentos para a barra. O rótulo acessível é montado aqui e não no
   * gráfico: é deste lado que se sabe que os valores são meticais e de que
   * lado (SIMO ou Banka) é a quota.
   */
  protected readonly barSegments = computed<readonly BarSegment[]>(() =>
    this.rows()
      .filter((row) => this.valueOf(row) > 0)
      .map((row) => ({
        key: row.key,
        label: row.label,
        value: this.valueOf(row),
        className: row.barClass,
        ariaLabel: `${row.label}: ${
          this.source() === 'difference'
            ? this.signedMzn(row.banka - row.simo)
            : this.mzn(this.valueOf(row))
        }, ${this.share(row)}`,
      })),
  );

  protected readonly activeRow = computed(
    () => this.rows().find((row) => row.key === this.active()) ?? null,
  );
  protected readonly totalSimo = computed(() =>
    this.rows().reduce((total, row) => total + row.simo, 0),
  );
  protected readonly totalBanka = computed(() =>
    this.rows().reduce((total, row) => total + row.banka, 0),
  );

  protected readonly totalDescription =
    'Soma de todos os fechos processados nesta execução, seja qual for a validação.';

  /**
   * Quota de cada estado no total do lado escolhido — o que a barra desenha.
   *
   * Calculadas todas de uma vez, e não uma a uma: arredondadas isoladamente não
   * fechariam 100%. Aqui só se mostra uma de cada vez, na legenda por baixo da
   * barra, mas quem soma os quatro segmentos com os olhos tem de chegar ao todo.
   */
  private readonly sharesByKey = computed(() => {
    const rows = this.rows();
    const shares = percentageShares(rows.map((row) => this.valueOf(row)));
    return new Map(rows.map((row, index) => [row.key, shares[index]]));
  });

  protected share(row: Row): string {
    return this.sharesByKey().get(row.key) ?? '0%';
  }

  protected widthOf(row: Row): number {
    const total = this.totalSimo();
    return total > 0 ? (row.simo / total) * 100 : 0;
  }

  protected mzn = formatMzn;
  protected signedMzn = formatSignedMzn;
  protected amount = formatAmount;
  protected signedAmount = formatSignedAmount;
  protected count = (value: number) => numberFormatter.format(value);
}
