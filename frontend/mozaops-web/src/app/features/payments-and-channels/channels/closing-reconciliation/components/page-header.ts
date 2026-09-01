import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';
import {
  LucideDownload,
  LucideInfo,
  LucideLoaderCircle,
  LucideRefreshCw,
  LucideShieldCheck,
} from '@lucide/angular';

import { formatInterval } from '../../../../../shared/format';
import type { ValidationResult } from '../data/models';

const dateTimeFormatter = new Intl.DateTimeFormat('pt-PT', {
  day: '2-digit',
  month: 'short',
  hour: '2-digit',
  minute: '2-digit',
});

/**
 * Cabeçalho da automação: quem é, de que execução se está a falar e o que se
 * pode fazer com ela.
 *
 * Era isto em dois componentes irmãos — um título e uma barra de execução — e
 * via-se: o título ao pé do ícone, e as etiquetas do período a começar lá
 * atrás, na margem da página, alinhadas com os cartões e não com o título de
 * que falam. Três faixas soltas onde só há uma ideia. Juntos, as etiquetas
 * penduram do título e as acções ficam à direita da mesma linha.
 */
@Component({
  selector: 'app-page-header',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [LucideDownload, LucideInfo, LucideLoaderCircle, LucideRefreshCw, LucideShieldCheck],
  template: `
    <header class="flex flex-wrap items-start justify-between gap-x-6 gap-y-4">
      <div class="flex min-w-0 items-start gap-3.5">
        <!-- Vermelho da marca, e em tom suave de propósito: cheio, um quadrado
             desta dimensão lia-se como aviso, e o vermelho aqui identifica a
             automação, não alerta para nada. É a mesma escolha que se fez no
             ícone activo da barra lateral. -->
        <span
          class="inline-flex size-11 shrink-0 items-center justify-center rounded-xl bg-alert-50 text-alert-600 ring-1 ring-alert-100"
        >
          <svg lucideShieldCheck [size]="22" [strokeWidth]="1.9"></svg>
        </span>

        <div class="flex min-w-0 flex-col gap-2">
          <div class="flex items-center gap-1.5">
            <h1 class="text-xl leading-tight font-bold text-gray-900">{{ title() }}</h1>

            <!-- A descrição é longa; fica arrumada num "i" e só aparece a pedido. -->
            <span class="group relative inline-flex">
              <button
                type="button"
                aria-label="Sobre esta funcionalidade"
                class="inline-flex size-6 shrink-0 items-center justify-center rounded-full text-gray-400 transition-colors hover:bg-moza-50 hover:text-moza-700 focus-visible:bg-moza-50 focus-visible:text-moza-700 focus-visible:outline-none"
              >
                <svg lucideInfo [size]="16" [strokeWidth]="2"></svg>
              </button>
              <span
                role="tooltip"
                class="pointer-events-none absolute top-full left-0 z-20 mt-2 w-72 rounded-xl bg-moza-800 px-3.5 py-2.5 text-xs leading-relaxed text-white opacity-0 shadow-lg transition-opacity duration-150 group-hover:opacity-100 group-focus-within:opacity-100 sm:w-80"
              >
                {{ description() }}
              </span>
            </span>
          </div>

          @if (result(); as r) {
            <div class="flex min-w-0 flex-wrap items-center gap-2">
              <span [class]="chip">
                Período
                <b class="max-w-52 truncate font-semibold text-gray-900">{{ period() }}</b>
              </span>

              <!-- Não há etiqueta do relatório: o nome dele é FECHO_POS_DOP mais o
                   período e o ano, ou seja, repetia o período que já está na
                   etiqueta ao lado — e só cabia cortado a meio. O nome vai no
                   title do botão que o descarrega, que é onde interessa, e o
                   browser mostra-o outra vez ao gravar. -->

              <!-- Os nomes dos três ficheiros vão no atributo title: são a
                   proveniência do resultado, mas ocupavam a barra toda à vista. -->
              <span [class]="chip" [title]="fileNames()">
                Executado
                <b class="max-w-52 truncate font-semibold text-gray-900">{{ executedAt() }}</b>
              </span>
            </div>
          }
        </div>
      </div>

      @if (result(); as r) {
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
            [title]="r.reportName + '.xlsx'"
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
      }
    </header>
  `,
})
export class PageHeaderComponent {
  readonly title = input.required<string>();
  readonly description = input.required<string>();

  /** Nulo enquanto não há execução, ou enquanto se está a criar outra. */
  readonly result = input<ValidationResult | null>(null);
  readonly downloading = input(false);

  readonly download = output<void>();
  readonly newExecution = output<void>();

  protected readonly chip =
    'inline-flex max-w-full items-center gap-1.5 rounded-full border border-gray-200 bg-white px-3 py-1.5 text-xs text-gray-500 shadow-sm';

  protected readonly period = computed(() => {
    const r = this.result();
    return r ? formatInterval(r.periodStart, r.periodEnd) : '';
  });

  protected readonly executedAt = computed(() => {
    const r = this.result();
    return r ? dateTimeFormatter.format(new Date(r.executedAt)) : '';
  });

  protected readonly fileNames = computed(() => {
    const r = this.result();
    if (!r) return '';
    const { posList, simoClosings, bankaCredits } = r.files;
    return [posList, simoClosings, bankaCredits].join(' · ');
  });
}
