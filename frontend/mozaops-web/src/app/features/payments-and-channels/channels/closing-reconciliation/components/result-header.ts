import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';
import { LucideDownload, LucideFileSpreadsheet, LucideLoaderCircle } from '@lucide/angular';

import { formatInterval, formatMzn, numberFormatter } from '../../../../../shared/format';
import { type Stat, StatCardComponent } from '../../../../../shared/ui/stat-card';
import type { ValidationResult } from '../data/models';

const dateTimeFormatter = new Intl.DateTimeFormat('pt-PT', {
  day: '2-digit',
  month: 'short',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
});

/** Cada cartão leva a sua própria leitura por baixo, em vez do intervalo repetido. */
interface StatWithNote {
  readonly stat: Stat;
  readonly note: string;
}

@Component({
  selector: 'app-result-header',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [StatCardComponent, LucideDownload, LucideFileSpreadsheet, LucideLoaderCircle],
  template: `
    <div class="flex flex-col gap-4 sm:gap-5">
      <div class="flex flex-wrap items-center justify-between gap-4">
        <div class="flex min-w-0 flex-col gap-1">
          <p class="text-sm text-gray-500">
            Resultado da validação — fechos de
            <span class="font-semibold text-gray-900">{{ period() }}</span>
          </p>
          <p class="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-gray-400">
            <span>Executada em {{ executedAt() }}</span>
            <span aria-hidden="true">·</span>
            <span class="inline-flex items-center gap-1">
              <svg lucideFileSpreadsheet [size]="13" [strokeWidth]="1.8"></svg>
              {{ result().reportName }}
            </span>
          </p>
        </div>

        <button
          type="button"
          (click)="download.emit()"
          [disabled]="downloading()"
          class="inline-flex items-center gap-2 rounded-xl bg-moza-700 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-moza-800 disabled:cursor-not-allowed disabled:opacity-50"
        >
          @if (downloading()) {
            <svg lucideLoaderCircle [size]="16" [strokeWidth]="2" class="animate-spin"></svg>
          } @else {
            <svg lucideDownload [size]="16" [strokeWidth]="2"></svg>
          }
          Transferir Relatório (.xlsx)
        </button>
      </div>

      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 sm:gap-5 xl:grid-cols-4">
        @for (item of stats(); track item.stat.id) {
          <app-stat-card [stat]="item.stat" [periodLabel]="item.note" />
        }
      </div>
    </div>
  `,
})
export class ResultHeaderComponent {
  readonly result = input.required<ValidationResult>();
  readonly downloading = input(false);
  readonly download = output<void>();

  protected readonly period = computed(() =>
    formatInterval(this.result().periodStart, this.result().periodEnd),
  );

  protected readonly executedAt = computed(() =>
    dateTimeFormatter.format(new Date(this.result().executedAt)),
  );

  protected readonly stats = computed<readonly StatWithNote[]>(() => {
    const s = this.result().summary;
    const n = (value: number) => numberFormatter.format(value);

    return [
      {
        stat: { id: 'processed', label: 'Fechos Processados', value: s.processed, icon: 'file-check' },
        note: `${this.period()} · ${n(s.divergent)} com divergência`,
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
          displayValue: formatMzn(s.divergenceAmount),
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
