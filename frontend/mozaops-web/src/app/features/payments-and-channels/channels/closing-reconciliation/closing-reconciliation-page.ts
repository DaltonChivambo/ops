import { ChangeDetectionStrategy, Component, computed, inject, input, signal } from '@angular/core';
import { LucideFileSearch, LucideLoaderCircle } from '@lucide/angular';

import { numberFormatter } from '../../../../shared/format';
import { findModule } from '../../../../core/navigation';
import { CardComponent } from '../../../../shared/ui/card';
import { ToastComponent } from '../../../../shared/ui/toast';
import { ExecutionBarComponent } from './components/execution-bar';
import { AmountReconciliationComponent } from './components/amount-reconciliation';
import { DiscrepancySourceDonutComponent } from './components/discrepancy-source-donut';
import { PageTitleComponent } from './components/page-title';
import { type CasePatch } from './components/pending-cases-table';
import { ResultTabsComponent } from './components/result-tabs';
import { UploadZoneComponent } from './components/upload-zone';
import { ReconciliationApi } from './data/reconciliation-api.service';
import type { ProgressPhase, UploadSlotId, ValidationResult } from './data/models';

/**
 * A página da automação: upload → execução → resultado.
 *
 * Porte de `client/src/modules/pos-closing/PosClosingPage.tsx`.
 */
@Component({
  selector: 'app-closing-reconciliation-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    AmountReconciliationComponent,
    CardComponent,
    DiscrepancySourceDonutComponent,
    ExecutionBarComponent,
    PageTitleComponent,
    ResultTabsComponent,
    ToastComponent,
    UploadZoneComponent,
    LucideFileSearch,
    LucideLoaderCircle,
  ],
  template: `
    <div class="flex flex-col gap-5">
      <app-page-title [title]="title()" [description]="description()" />

      @if (loading()) {
        <section appCard class="flex items-center justify-center gap-3 py-16 text-sm text-gray-500">
          <svg lucideLoaderCircle [size]="18" [strokeWidth]="2" class="animate-spin"></svg>
          A carregar a última execução…
        </section>
      } @else if (!result() || uploading()) {
        <!-- Sem execução, ou a criar uma nova: só o formulário. -->
        <app-upload-zone
          [processing]="processing()"
          [phase]="phase()"
          [error]="error()"
          [cancellable]="result() !== null"
          (cancelled)="uploading.set(false)"
          (executed)="execute($event)"
        />

        @if (!result() && !processing()) {
          <section appCard class="flex flex-col items-center gap-3 py-12 text-center">
            <span
              class="inline-flex size-12 items-center justify-center rounded-xl bg-moza-100 text-moza-700"
            >
              <svg lucideFileSearch [size]="24" [strokeWidth]="1.8"></svg>
            </span>
            <p class="font-semibold text-gray-900">Nenhuma validação executada</p>
            <p class="max-w-sm text-sm text-gray-500">
              Carregue os três ficheiros acima para reconciliar os fechos da SIMO com os créditos
              efectuados no Banka.
            </p>
          </section>
        }
      } @else if (result(); as current) {
        <app-execution-bar
          [result]="current"
          [downloading]="downloading()"
          (download)="download()"
          (newExecution)="startNewExecution()"
        />

        <!-- O apuramento por estado — os fechos por tratar e os montantes dos dois
             lados — esteve num separador «Resumo por Estado». É leitura e não
             navegação: fica à vista, antes das listas. -->
        <div
          class="grid grid-cols-1 gap-4 sm:gap-5 lg:grid-cols-[minmax(17rem,1fr)_minmax(0,2fr)]"
        >
          <app-discrepancy-source-donut [summary]="current.summary" />
          <app-amount-reconciliation [summary]="current.summary" />
        </div>

        <app-result-tabs [result]="current" (updateCase)="updateCase($event)" />
      }

      @if (success(); as message) {
        <app-toast [message]="message" (dismiss)="success.set(null)" />
      }
      @if (error(); as message) {
        <app-toast [message]="message" variant="error" (dismiss)="error.set(null)" />
      }
    </div>
  `,
})
export class ClosingReconciliationPageComponent {
  private readonly api = inject(ReconciliationApi);

  /**
   * Ambos chegam por `withComponentInputBinding()`, directamente dos parâmetros
   * de rota. O título e a descrição saem do catálogo em vez de virem por `data`
   * da rota: é lá que a funcionalidade está definida, e duplicá-los na tabela de
   * rotas era um segundo sítio para os manter em dia.
   */
  readonly moduleId = input.required<string>();
  readonly featureId = input.required<string>();

  private readonly feature = computed(() =>
    findModule(this.moduleId())?.features.find((item) => item.id === this.featureId()),
  );

  protected readonly title = computed(
    () => this.feature()?.title ?? 'Validação de Crédito de Valores de Fecho',
  );
  protected readonly description = computed(() => this.feature()?.description ?? '');

  protected readonly result = signal<ValidationResult | null>(null);
  protected readonly loading = signal(true);
  protected readonly processing = signal(false);
  protected readonly phase = signal<ProgressPhase | null>(null);
  protected readonly error = signal<string | null>(null);
  protected readonly success = signal<string | null>(null);
  protected readonly downloading = signal(false);
  /** O formulário de upload só ocupa o ecrã quando é isso que se está a fazer. */
  protected readonly uploading = signal(false);

  constructor() {
    // A última execução está persistida no servidor: sobrevive ao refresh.
    void this.api
      .getLatestResult()
      .then((latest) => this.result.set(latest))
      .catch(() =>
        this.error.set(
          'Não foi possível carregar a última execução. Confirme que o servidor está a correr.',
        ),
      )
      .finally(() => this.loading.set(false));
  }

  protected async execute(files: Record<UploadSlotId, File>): Promise<void> {
    this.processing.set(true);
    this.error.set(null);
    this.success.set(null);
    // O upload e a reconciliação são um único round-trip: assim que o pedido
    // parte, a fase que interessa mostrar é a que o servidor está a fazer.
    this.phase.set('upload');

    const outcome = await this.api.runValidation(files);

    if (outcome.ok) {
      this.result.set(outcome.result);
      this.uploading.set(false);
      this.success.set(
        `Validação concluída — ${numberFormatter.format(outcome.result.summary.processed)} fechos processados.`,
      );
    } else {
      this.error.set(outcome.message);
    }

    this.processing.set(false);
    this.phase.set(null);
  }

  protected async updateCase({ caseId, patch }: CasePatch): Promise<void> {
    const current = this.result();
    if (!current) return;

    try {
      const { case: updated, summary } = await this.api.updateCase(caseId, patch);
      this.result.set({
        ...current,
        summary,
        cases: current.cases.map((item) => (item.id === updated.id ? updated : item)),
      });
    } catch {
      this.error.set('Não foi possível actualizar o caso. Tente novamente.');
    }
  }

  protected async download(): Promise<void> {
    const current = this.result();
    if (!current || this.downloading()) return;

    this.downloading.set(true);
    try {
      await this.api.downloadReport(current.executionId, current.reportName);
    } catch {
      this.error.set('Não foi possível gerar o relatório. Tente novamente.');
    } finally {
      this.downloading.set(false);
    }
  }

  protected startNewExecution(): void {
    this.success.set(null);
    this.error.set(null);
    this.uploading.set(true);
  }
}
