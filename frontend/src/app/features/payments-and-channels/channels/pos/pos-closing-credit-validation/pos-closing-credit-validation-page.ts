import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  input,
  signal,
} from '@angular/core';
import { LucideFileSearch, LucideLoaderCircle } from '@lucide/angular';

import { numberFormatter } from '../../../../../shared/format';
import { ApiError } from '../../../../../core/http/api-error';
import { findModule } from '../../../../../core/navigation';
import { CardComponent } from '../../../../../shared/ui/card';
import { ToastComponent, type Toast } from '../../../../../shared/ui/toast';
import { AmountReconciliationComponent } from './components/amount-reconciliation';
import { DiscrepancySourceDonutComponent } from './components/discrepancy-source-donut';
import { PageHeaderComponent } from './components/page-header';
import { ResultStatsComponent } from './components/result-stats';
import { ResultTabsComponent } from './components/result-tabs';
import { UploadZoneComponent } from './components/upload-zone';
import { ReconciliationApi } from './data/reconciliation-api.service';
import type {
  CaseMatches,
  CasePatch,
  PendingCase,
  ProgressPhase,
  ReconciliationCandidate,
  SlaSettings,
  UploadSlotId,
  ValidationResult,
} from './data/models';
import { DEFAULT_SLA } from './data/sla';

/**
 * A página da automação: upload → execução → resultado.
 *
 * Porte de `client/src/modules/pos-closing/PosClosingPage.tsx`.
 */
@Component({
  selector: 'app-pos-closing-credit-validation-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    AmountReconciliationComponent,
    CardComponent,
    DiscrepancySourceDonutComponent,
    PageHeaderComponent,
    ResultStatsComponent,
    ResultTabsComponent,
    ToastComponent,
    UploadZoneComponent,
    LucideFileSearch,
    LucideLoaderCircle,
  ],
  template: `
    <div class="flex flex-col gap-5">
      <!-- As etiquetas e as acções da execução vivem aqui, no cabeçalho, e não
           numa faixa própria: enquanto se carrega, ou enquanto se prepara outra
           execução, não há execução de que falar e o cabeçalho fica só com o
           título. -->
      <app-page-header
        [heading]="title()"
        [description]="description()"
        [result]="uploading() ? null : result()"
        [downloading]="downloading()"
        [settings]="settings()"
        (download)="download()"
        (newExecution)="startNewExecution()"
        (settingsChanged)="saveSettings($event)"
      />

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
          [error]="error()?.detail ?? null"
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
        <app-result-stats [result]="current" />

        <!-- O apuramento por estado — os fechos por tratar e os montantes dos dois
             lados — esteve num separador «Resumo por Estado». É leitura e não
             navegação: fica à vista, antes das listas.

             Lado a lado só quando sobram ~1024px de conteúdo: a tabela dos
             montantes tem cinco colunas e um mínimo de 36rem, e com menos do que
             isso a coluna que lhe sobrava obrigava-a a scroll horizontal
             próprio. O limiar depende da barra lateral estar aberta ou não —
             ver a nota no result-stats. -->
        <div
          class="grid grid-cols-1 gap-4 sm:gap-5 min-[1360px]:grid-cols-[minmax(18rem,1fr)_minmax(0,2fr)] min-[1170px]:group-data-[sidebar=collapsed]/shell:grid-cols-[minmax(18rem,1fr)_minmax(0,2fr)]"
        >
          <app-discrepancy-source-donut [summary]="current.summary" />
          <app-amount-reconciliation [summary]="current.summary" />
        </div>

        <app-result-tabs
          [result]="current"
          [settings]="settings()"
          [revision]="detailsRevision()"
          [reconciling]="reconciling()"
          [reconciliationCandidates]="reconciliationCandidates()"
          (updateCase)="updateCase($event)"
          (reconcileCase)="reconcileCase($event)"
          (reconcileCases)="reconcileCases($event)"
        />
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
export class PosClosingCreditValidationPageComponent {
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
    () => this.feature()?.title ?? 'Validação de Crédito de Valores de Fecho de POS',
  );
  protected readonly description = computed(() => this.feature()?.description ?? '');

  protected readonly result = signal<ValidationResult | null>(null);
  protected readonly loading = signal(true);
  protected readonly processing = signal(false);
  protected readonly phase = signal<ProgressPhase | null>(null);
  protected readonly error = signal<Toast | null>(null);
  protected readonly success = signal<Toast | null>(null);
  protected readonly downloading = signal(false);
  /**
   * Versão dos fechos no servidor. Uma conciliação muda o estado de fechos que a
   * tabela já carregou — sobe-se isto, e ela recarrega.
   */
  protected readonly detailsRevision = signal(0);
  /** Uma conciliação em lote a gravar — o botão do cartão espera por ela. */
  protected readonly reconciling = signal(false);
  /** As chaves que se conciliam com crédito igual — `null` enquanto se pedem. */
  protected readonly reconciliationCandidates = signal<readonly ReconciliationCandidate[] | null>(
    null,
  );
  /** O formulário de upload só ocupa o ecrã quando é isso que se está a fazer. */
  protected readonly uploading = signal(false);
  /** O prazo de tratamento em vigor. Falhar a leitura não tranca o ecrã: o
   *  valor por omissão serve, e a gravação volta a tentar. */
  protected readonly settings = signal<SlaSettings>(DEFAULT_SLA);

  constructor() {
    // A lista de conciliações volta a pedir-se sempre que o resultado muda: uma
    // conciliação, uma mudança de fase ou uma execução nova mudam quais chaves
    // entram. A lista anterior fica à vista até a nova chegar.
    effect((onCleanup) => {
      const current = this.result();
      if (!current) {
        this.reconciliationCandidates.set(null);
        return;
      }

      let cancelled = false;
      onCleanup(() => {
        cancelled = true;
      });

      void this.api
        .listReconciliationCandidates(current.executionId)
        .then((candidates) => {
          if (!cancelled) this.reconciliationCandidates.set(candidates);
        })
        .catch(() => {
          if (cancelled) return;
          this.reconciliationCandidates.set([]);
          this.error.set({
            title: 'Períodos duplicados indisponíveis',
            detail: 'Não foi possível carregá-los. Tente recarregar a página.',
          });
        });
    });

    // A última execução está persistida no servidor: sobrevive ao refresh.
    void this.api
      .getLatestResult()
      .then((latest) => this.result.set(latest))
      .catch(() =>
        this.error.set({
          title: 'Última execução indisponível',
          detail: 'Não foi possível carregá-la. Confirme que o servidor está a correr.',
        }),
      )
      .finally(() => this.loading.set(false));

    void this.api
      .getSettings()
      .then((settings) => this.settings.set(settings))
      .catch(() => undefined);
  }

  protected async saveSettings(patch: {
    caseSlaDays: number;
    caseWarningDays: number;
  }): Promise<void> {
    try {
      this.settings.set(await this.api.saveSettings(patch));
      this.success.set({
        title: 'Prazo actualizado',
        detail: `Os casos passam a ter ${patch.caseSlaDays} dias para ser tratados.`,
      });
    } catch (problem) {
      this.error.set({
        title: 'Prazo não guardado',
        detail:
          problem instanceof ApiError
            ? problem.message
            : 'Não foi possível guardar. Tente novamente.',
      });
    }
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
      this.success.set(executionToast(outcome.result));
    } else {
      this.error.set({ title: 'Validação não executada', detail: outcome.message });
    }

    this.processing.set(false);
    this.phase.set(null);
  }

  protected async updateCase({ caseId, patch }: CasePatch): Promise<void> {
    const current = this.result();
    if (!current) return;

    const before = current.cases.find((item) => item.id === caseId);

    try {
      const { case: updated, summary } = await this.api.updateCase(caseId, patch);
      this.result.set({
        ...current,
        summary,
        cases: current.cases.map((item) => (item.id === updated.id ? updated : item)),
      });

      // Regularizar tira o caso da fila, e reabrir devolve-o: sem aviso, a linha
      // simplesmente desaparecia de uma lista e aparecia na outra.
      const pos = posLabel(updated);
      if (updated.status === 'resolved' && before?.status !== 'resolved') {
        this.success.set({
          title: 'Caso regularizado',
          detail: `${pos} passou para «Regularizados».`,
        });
      } else if (before?.status === 'resolved' && updated.status !== 'resolved') {
        this.success.set({ title: 'Caso reaberto', detail: `${pos} voltou aos casos em aberto.` });
      } else {
        this.success.set({ title: 'Caso actualizado', detail: pos });
      }
    } catch (problem) {
      // Uma recusa do servidor (e-Ticket sem forma de referência, estado que não
      // existe) traz a razão em português; só o resto fica com a mensagem genérica.
      this.error.set({
        title: 'Caso não actualizado',
        detail:
          problem instanceof ApiError && problem.status === 422
            ? problem.message
            : 'Não foi possível guardar a alteração. Tente novamente.',
      });
    }
  }

  protected async reconcileCase({ caseId, matches }: CaseMatches): Promise<void> {
    const current = this.result();
    if (!current) return;

    const before = current.cases.find((item) => item.id === caseId);

    try {
      const { case: updated, summary } = await this.api.reconcileCase(caseId, matches);
      // O `summary` já vem com os fechos conciliados em «confere»: os gráficos e
      // os indicadores lêem-no daqui e acompanham sozinhos. A tabela de fechos
      // não — vai buscá-los ao servidor —, por isso recarrega.
      this.result.set({
        ...current,
        summary,
        cases: current.cases.map((item) => (item.id === updated.id ? updated : item)),
      });
      this.detailsRevision.update((revision) => revision + 1);

      // Conciliar todos os fechos regulariza o caso, e ele sai da fila — dito,
      // como no `updateCase`, para a linha não desaparecer sem explicação.
      const pos = posLabel(updated);
      if (updated.status === 'resolved' && before?.status !== 'resolved') {
        this.success.set({
          title: 'Fechos conciliados',
          detail: `${pos} — o caso passou para «Regularizados».`,
        });
      } else {
        this.success.set({ title: 'Conciliação guardada', detail: pos });
      }
    } catch (problem) {
      // Um par que o servidor recusa (valor diferente, crédito já usado) traz a
      // razão em português; só o resto fica com a mensagem genérica.
      this.error.set({
        title: 'Conciliação não guardada',
        detail:
          problem instanceof ApiError && problem.status === 422
            ? problem.message
            : 'Não foi possível guardar. Tente novamente.',
      });
    }
  }

  protected async reconcileCases(items: readonly CaseMatches[]): Promise<void> {
    const current = this.result();
    if (!current || this.reconciling()) return;

    this.reconciling.set(true);
    try {
      const { cases, summary } = await this.api.reconcileCases(current.executionId, items);
      const updated = new Map(cases.map((item) => [item.id, item]));
      // Como numa conciliação de um caso: o `summary` actualiza gráficos e
      // indicadores, os casos novos tiram as chaves da fila, e a tabela de
      // fechos recarrega com os estados novos.
      this.result.set({
        ...current,
        summary,
        cases: current.cases.map((item) => updated.get(item.id) ?? item),
      });
      this.detailsRevision.update((revision) => revision + 1);

      const closings = items.reduce((total, item) => total + item.matches.length, 0);
      this.success.set({
        title: 'Períodos duplicados conciliados',
        facts: [
          { label: 'Chaves conciliadas', value: count(items.length) },
          { label: 'Fechos em «Crédito confere»', value: count(closings) },
          {
            label: 'Casos regularizados',
            value: count(cases.filter((item) => item.status === 'resolved').length),
          },
        ],
      });
    } catch (problem) {
      // O servidor concilia todos ou nenhum: numa recusa nada ficou gravado, e a
      // mensagem diz qual POS a provocou.
      this.error.set({
        title: 'Nada foi conciliado',
        detail:
          problem instanceof ApiError && problem.status === 422
            ? problem.message
            : 'Não foi possível conciliar as chaves. Tente novamente.',
      });
    } finally {
      this.reconciling.set(false);
    }
  }

  protected async download(): Promise<void> {
    const current = this.result();
    if (!current || this.downloading()) return;

    this.downloading.set(true);
    try {
      await this.api.downloadReport(current.executionId, current.reportName);
    } catch {
      this.error.set({
        title: 'Relatório não gerado',
        detail: 'Não foi possível gerar o relatório. Tente novamente.',
      });
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

const count = (value: number): string => numberFormatter.format(value);

const posLabel = (item: PendingCase): string => `POS ${item.posId} · período ${item.period}`;

/**
 * O resumo de uma execução acabada: os números que dizem como correu, cada um na
 * sua linha. Um extracto do Banka com movimentos repetidos não pára a execução —
 * descartam-se —, mas o operador tem de saber que o ficheiro vinha assim.
 */
function executionToast({ reportName, summary }: ValidationResult): Toast {
  const repeated = summary.bankaDuplicatesDiscarded ?? 0;
  return {
    title: 'Validação concluída',
    detail: reportName,
    facts: [
      { label: 'Fechos processados', value: count(summary.processed) },
      {
        label: 'Taxa de validação',
        value: `${summary.validationRate.toLocaleString('pt-PT', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`,
      },
      {
        label: 'Casos para análise',
        value: count(summary.openCases),
        tone: summary.openCases > 0 ? 'warning' : 'neutral',
      },
      ...(repeated > 0
        ? [
            {
              label: 'Movimentos repetidos ignorados (Banka)',
              value: count(repeated),
              tone: 'warning' as const,
            },
          ]
        : []),
    ],
  };
}
