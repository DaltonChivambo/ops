import { ChangeDetectionStrategy, Component, computed, input, output, signal } from '@angular/core';
import {
  LucideFileCheckCorner,
  LucideLoaderCircle,
  LucideTriangleAlert,
  LucideUpload,
  LucideX,
} from '@lucide/angular';

import { CardComponent } from '../../../../../shared/ui/card';
import type { ProgressPhase, UploadSlotId } from '../data/models';

interface SlotConfig {
  readonly id: UploadSlotId;
  readonly label: string;
  readonly hint: string;
}

const SLOTS: readonly SlotConfig[] = [
  { id: 'posList', label: 'Lista de POS', hint: 'Portal SIMO · POS > Lista' },
  { id: 'simoClosings', label: 'Fechos SIMO', hint: 'Portal SIMO · POS > Fechos' },
  { id: 'bankaCredits', label: 'Créditos Banka', hint: 'MIS / MicroStrategy' },
];

const PHASE_LABELS: Record<ProgressPhase, string> = {
  upload: 'A enviar os ficheiros para o servidor…',
  reconciliation: 'A reconciliar fechos SIMO com créditos Banka…',
};

/** Os três ficheiros e o botão que dispara a execução — a selecção vive aqui, não sobe até estar completa. */
@Component({
  selector: 'app-upload-zone',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CardComponent,
    LucideFileCheckCorner,
    LucideLoaderCircle,
    LucideTriangleAlert,
    LucideUpload,
    LucideX,
  ],
  template: `
    <section appCard class="flex flex-col gap-5">
      <div class="flex items-start justify-between gap-4">
        <div>
          <h2 class="text-[1.0625rem] font-bold">Nova Validação</h2>
          <p class="mt-1 text-sm text-gray-500">
            Carregue os três ficheiros extraídos do SIMO e do Banka (MIS).
          </p>
        </div>

        <!-- Só há «fechar» quando já existe um resultado por trás para onde
             voltar; na primeira execução não há nada que cancelar. -->
        @if (cancellable() && !processing()) {
          <button
            type="button"
            (click)="cancelled.emit()"
            aria-label="Fechar"
            class="inline-flex size-8 shrink-0 items-center justify-center rounded-full text-gray-400 transition-colors hover:bg-gray-50 hover:text-gray-900"
          >
            <svg lucideX [size]="18" [strokeWidth]="2"></svg>
          </button>
        }
      </div>

      <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
        @for (slot of slots; track slot.id) {
          @let picked = files()[slot.id];

          <label
            class="flex cursor-pointer flex-col items-center gap-2 rounded-xl px-4 py-5 text-center transition-colors"
            [class]="
              picked
                ? 'border-2 border-emerald-200 bg-emerald-50/40'
                : 'border-2 border-dashed border-gray-200 hover:border-moza-300 hover:bg-moza-50/40'
            "
          >
            <input
              type="file"
              accept=".xlsx,.xls"
              class="sr-only"
              [disabled]="processing()"
              (change)="pick(slot.id, $event)"
            />

            @if (picked) {
              <svg
                lucideFileCheckCorner
                [size]="22"
                [strokeWidth]="1.8"
                class="text-emerald-600"
              ></svg>
            } @else {
              <svg lucideUpload [size]="22" [strokeWidth]="1.8" class="text-gray-400"></svg>
            }

            <span class="text-sm font-semibold text-gray-900">{{ slot.label }}</span>
            <span class="max-w-full truncate text-xs text-gray-500">
              {{ picked ? picked.name : 'Selecionar ficheiro' }}
            </span>
            <span class="text-[0.6875rem] tracking-wide text-gray-400 uppercase">
              {{ slot.hint }}
            </span>
          </label>
        }
      </div>

      <div class="flex flex-wrap items-center gap-4">
        <button
          type="button"
          (click)="execute()"
          [disabled]="!complete() || processing()"
          class="inline-flex items-center gap-2 rounded-xl bg-moza-700 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-moza-800 disabled:cursor-not-allowed disabled:opacity-50"
        >
          @if (processing()) {
            <svg lucideLoaderCircle [size]="16" [strokeWidth]="2" class="animate-spin"></svg>
          }
          Executar Validação
        </button>

        @if (processing() && phase()) {
          <span class="text-sm text-gray-500">{{ phaseLabel() }}</span>
        }
      </div>

      <!-- A excepção de negócio do PDD: é conteúdo para o operador ler, e por
           isso fica no fluxo da página em vez de num aviso que se desvanece. -->
      @if (error() && !processing()) {
        <div
          class="flex items-start gap-3 rounded-xl bg-alert-50 px-4 py-3 text-sm text-alert-700"
        >
          <svg lucideTriangleAlert [size]="18" [strokeWidth]="1.8" class="mt-0.5 shrink-0"></svg>
          <span>
            <span class="font-semibold">Exceção de negócio: </span>{{ error() }}
          </span>
        </div>
      }
    </section>
  `,
})
export class UploadZoneComponent {
  readonly processing = input(false);
  readonly phase = input<ProgressPhase | null>(null);
  readonly error = input<string | null>(null);
  /** Verdadeiro quando já existe uma execução — permite fechar sem executar. */
  readonly cancellable = input(false);

  readonly cancelled = output<void>();
  readonly executed = output<Record<UploadSlotId, File>>();

  protected readonly slots = SLOTS;
  protected readonly files = signal<Partial<Record<UploadSlotId, File>>>({});

  protected readonly complete = computed(() => {
    const picked = this.files();
    return SLOTS.every((slot) => picked[slot.id] !== undefined);
  });

  protected readonly phaseLabel = computed(() => {
    const phase = this.phase();
    return phase ? PHASE_LABELS[phase] : '';
  });

  protected pick(slot: UploadSlotId, event: Event): void {
    const selected = (event.target as HTMLInputElement).files?.[0];
    if (selected) this.files.update((current) => ({ ...current, [slot]: selected }));
  }

  protected execute(): void {
    if (!this.complete() || this.processing()) return;
    this.executed.emit(this.files() as Record<UploadSlotId, File>);
  }
}
