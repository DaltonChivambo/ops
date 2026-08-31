import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
  output,
  signal,
  viewChild,
  type ElementRef,
} from '@angular/core';
import { LucideTriangleAlert } from '@lucide/angular';

import { numberFormatter } from '../../../../../shared/format';
import type { ValidationResult } from '../data/models';
import { type CasePatch, PendingCasesTableComponent } from './pending-cases-table';
import { ReconciliationTableComponent } from './reconciliation-table';

type TabId = 'cases' | 'closings';

/** Separadores dos resultados — só um montado de cada vez; por omissão mostra todos os fechos. */
@Component({
  selector: 'app-result-tabs',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [PendingCasesTableComponent, ReconciliationTableComponent, LucideTriangleAlert],
  template: `
    @let r = result();

    <div class="flex flex-col gap-4">
      @if (dataQuality().length > 0) {
        <div
          class="flex items-start gap-2.5 rounded-xl bg-amber-50 px-4 py-3 text-sm ring-1 ring-amber-100"
        >
          <svg
            lucideTriangleAlert
            [size]="16"
            [strokeWidth]="1.9"
            class="mt-0.5 shrink-0 text-amber-600"
          ></svg>
          <div class="flex min-w-0 flex-col gap-0.5">
            <span class="font-semibold text-amber-800">Qualidade dos dados de entrada</span>
            <span class="text-amber-700">{{ dataQuality().join(' · ') }}.</span>
          </div>
        </div>
      }

      <div
        #tabList
        role="tablist"
        aria-label="Vistas do resultado"
        class="flex max-w-full items-center gap-7 overflow-x-auto border-b border-gray-200"
      >
        @for (item of tabs(); track item.id) {
          @let active = tab() === item.id;

          <!-- Vermelho só na barra: aponta o separador aberto, o rótulo fica preto. -->
          <button
            type="button"
            role="tab"
            [attr.aria-selected]="active"
            (click)="tab.set(item.id)"
            class="-mb-px inline-flex shrink-0 items-center gap-2 border-b-2 px-1 py-3 text-sm font-semibold transition-colors"
            [class]="
              active
                ? 'border-alert-500 text-gray-900'
                : 'border-transparent text-gray-400 hover:text-gray-700'
            "
          >
            {{ item.label }}
            <span
              class="text-[0.72rem] font-semibold tabular-nums"
              [class]="active ? 'text-gray-400' : 'text-gray-300'"
            >
              {{ item.badge }}
            </span>
          </button>
        }
      </div>

      @if (tab() === 'cases') {
        <app-pending-cases-table
          [cases]="r.cases"
          [scrollAnchor]="anchor()"
          (updated)="updateCase.emit($event)"
        />
      } @else {
        <app-reconciliation-table [executionId]="r.executionId" [scrollAnchor]="anchor()" />
      }
    </div>
  `,
})
export class ResultTabsComponent {
  readonly result = input.required<ValidationResult>();
  readonly updateCase = output<CasePatch>();

  /** Âncora do `appPageFirstScroll`: os separadores, não a tabela, para ficarem à vista. */
  private readonly tabList = viewChild<ElementRef<HTMLElement>>('tabList');
  protected readonly anchor = computed(() => this.tabList()?.nativeElement);

  protected readonly tab = signal<TabId>('closings');

  protected readonly dataQuality = computed(() => {
    const { keyCollisions, unregisteredPos } = this.result().summary;
    const notes: string[] = [];
    if (unregisteredPos > 0) {
      notes.push(`${this.n(unregisteredPos)} POS sem cadastro na Lista de POS`);
    }
    if (keyCollisions > 0) {
      notes.push(`${this.n(keyCollisions)} chave(s) com períodos que colidem em módulo 1000`);
    }
    return notes;
  });

  protected readonly tabs = computed(() => {
    const summary = this.result().summary;
    return [
      { id: 'closings' as const, label: 'Todos os Fechos', badge: this.n(summary.processed) },
      { id: 'cases' as const, label: 'Casos para Análise', badge: this.n(summary.openCases) },
    ];
  });

  private n = (value: number) => numberFormatter.format(value);
}
