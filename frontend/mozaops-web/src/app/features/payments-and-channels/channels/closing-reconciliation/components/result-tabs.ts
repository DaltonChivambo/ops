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

      <!-- Colado ao topo enquanto se percorre a lista: sem isto os separadores
           saíam do ecrã e ficava-se sem forma de trocar de vista sem voltar
           atrás. O appPageFirstScroll já tentava segurá-los, mas só trata da
           roda do rato — num tablet o gesto é toque e passava-lhes ao lado. -->
      <!-- A referência fica AQUI, no elemento que cola, e não na pastilha lá dentro:
           é a ele que o appPageFirstScroll pergunta quanto falta para assentar, e
           só ele sabe onde assenta. -->
      <div #tabList class="sticky top-[var(--app-header-h)] z-20 -mx-1 bg-[#f7f6fb] px-1 py-2">
        <!-- Controlo segmentado, o mesmo que o filtro de estado da tabela de casos
             já usa. O sublinhado anterior deixava os separadores inactivos com cara
             de texto morto: não se percebia que eram para carregar. Aqui a moldura
             diz que são opções e o fundo branco diz qual está escolhida. -->
        <div
          role="tablist"
          aria-label="Vistas do resultado"
          class="inline-flex max-w-full gap-1 overflow-x-auto rounded-xl border border-gray-100 bg-gray-50 p-1"
        >
          @for (item of tabs(); track item.id) {
            @let active = tab() === item.id;

            <button
              type="button"
              role="tab"
              [attr.aria-selected]="active"
              (click)="tab.set(item.id)"
              class="inline-flex shrink-0 cursor-pointer items-center gap-2 rounded-lg px-3.5 py-2 text-sm font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-moza-400"
              [class]="
                active
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-500 hover:bg-white/70 hover:text-gray-900'
              "
            >
              {{ item.label }}
              <span
                class="rounded-full px-1.5 py-0.5 text-2xs font-bold tabular-nums transition-colors"
                [class]="active ? 'bg-moza-100 text-moza-700' : 'bg-gray-200 text-gray-500'"
              >
                {{ item.badge }}
              </span>
            </button>
          }
        </div>
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
