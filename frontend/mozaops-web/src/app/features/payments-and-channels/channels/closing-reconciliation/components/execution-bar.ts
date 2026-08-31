import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';
import { LucideDownload, LucideLoaderCircle, LucideRefreshCw } from '@lucide/angular';

import { formatInterval } from '../../../../../shared/format';
import type { ValidationResult } from '../data/models';

const dateTimeFormatter = new Intl.DateTimeFormat('pt-PT', {
  day: '2-digit',
  month: 'short',
  hour: '2-digit',
  minute: '2-digit',
});

/** Contexto da execução, em etiquetas, e as duas acções — substitui o cartão de upload com resultado. */
@Component({
  selector: 'app-execution-bar',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [LucideDownload, LucideLoaderCircle, LucideRefreshCw],
  template: `
    @let r = result();

    <section class="flex flex-wrap items-center justify-between gap-3">
      <div class="flex min-w-0 flex-wrap items-center gap-2">
        <span [class]="chip">
          Período
          <b class="max-w-52 truncate font-semibold text-gray-900">{{ period() }}</b>
        </span>

        <span [class]="chip" [title]="r.reportName">
          Relatório
          <b class="max-w-52 truncate font-semibold text-gray-900">{{ r.reportName }}</b>
        </span>

        <!-- Os nomes dos três ficheiros vão no atributo title: são a
             proveniência do resultado, mas ocupavam a barra toda à vista. -->
        <span [class]="chip" [title]="fileNames()">
          Executado
          <b class="max-w-52 truncate font-semibold text-gray-900">{{ executedAt() }}</b>
        </span>
      </div>

      <div class="flex flex-wrap items-center gap-2.5">
        <button
          type="button"
          (click)="newExecution.emit()"
          class="inline-flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-4 py-2.5 text-sm font-semibold text-gray-600 shadow-sm transition-colors hover:bg-gray-50 hover:text-gray-900"
        >
          <svg lucideRefreshCw [size]="16" [strokeWidth]="1.8"></svg>
          Nova execução
        </button>

        <button
          type="button"
          (click)="download.emit()"
          [disabled]="downloading()"
          class="inline-flex items-center gap-2 rounded-xl bg-moza-700 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-moza-800 disabled:cursor-not-allowed disabled:opacity-50"
        >
          @if (downloading()) {
            <svg lucideLoaderCircle [size]="16" [strokeWidth]="2" class="animate-spin"></svg>
          } @else {
            <svg lucideDownload [size]="16" [strokeWidth]="2"></svg>
          }
          Descarregar relatório
        </button>
      </div>
    </section>
  `,
})
export class ExecutionBarComponent {
  readonly result = input.required<ValidationResult>();
  readonly downloading = input(false);

  readonly download = output<void>();
  readonly newExecution = output<void>();

  protected readonly chip =
    'inline-flex max-w-full items-center gap-1.5 rounded-full border border-gray-200 bg-white px-3 py-1.5 text-xs text-gray-500 shadow-sm';

  protected readonly period = computed(() =>
    formatInterval(this.result().periodStart, this.result().periodEnd),
  );

  protected readonly executedAt = computed(() =>
    dateTimeFormatter.format(new Date(this.result().executedAt)),
  );

  protected readonly fileNames = computed(() => {
    const { posList, simoClosings, bankaCredits } = this.result().files;
    return [posList, simoClosings, bankaCredits].join(' · ');
  });
}
