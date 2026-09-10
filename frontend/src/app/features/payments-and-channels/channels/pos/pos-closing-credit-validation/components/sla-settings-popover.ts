import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  ElementRef,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { LucideSettings2 } from '@lucide/angular';

import { formatDate } from '../../../../../../shared/format';
import { InfoTooltipComponent } from '../../../../../../shared/ui/info-tooltip';
import type { SlaSettings } from '../data/models';
import { MAX_SLA_DAYS } from '../data/sla';

/**
 * Onde o DOP muda o prazo de tratamento — sem pedir nada à equipa técnica.
 *
 * O invariante («o aviso vem antes do prazo») é o mesmo que o servidor valida;
 * repeti-lo aqui é só para o botão não deixar submeter o que ia voltar em erro.
 */
@Component({
  selector: 'app-sla-settings-popover',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [LucideSettings2, InfoTooltipComponent],
  host: {
    class: 'relative shrink-0',
    '(document:mousedown)': 'onDocumentMouseDown($event)',
    '(document:keydown.escape)': 'open.set(false)',
  },
  template: `
    <button
      type="button"
      (click)="toggle()"
      aria-haspopup="true"
      [attr.aria-expanded]="open()"
      class="inline-flex items-center gap-2 rounded-xl border border-gray-100 bg-gray-50 px-3.5 py-2.5 text-sm font-semibold text-gray-600 transition-colors hover:text-gray-900"
    >
      <svg lucideSettings2 [size]="15" [strokeWidth]="2" class="shrink-0"></svg>
      Prazo: {{ settings().caseSlaDays }}d
    </button>

    @if (open()) {
      <div
        class="absolute right-0 z-20 mt-1.5 w-72 rounded-xl border border-gray-100 bg-white p-4 shadow-lg"
      >
        <div class="flex items-center gap-1.5">
          <h3 class="text-2xs font-bold tracking-wider text-gray-400 uppercase">
            Prazo de tratamento
          </h3>
          <app-info-tooltip
            text="Conta a partir da data do fecho na SIMO — não da data em que a validação correu. Muda para todos os casos, incluindo os de execuções anteriores."
            label="Como o prazo é contado"
          />
        </div>

        <label class="mt-3 flex items-center justify-between gap-3">
          <span class="text-sm text-gray-600">Prazo, em dias</span>
          <input
            type="number"
            min="1"
            [max]="maxDays"
            [value]="slaDays()"
            (input)="slaDays.set(number($event))"
            class="w-20 rounded-lg border border-gray-200 bg-white px-2.5 py-1.5 text-sm font-semibold text-gray-900 tabular-nums outline-none focus:border-moza-400 focus:ring-2 focus:ring-moza-100"
          />
        </label>

        <label class="mt-2.5 flex items-center justify-between gap-3">
          <span class="text-sm text-gray-600">Avisar, dias antes</span>
          <input
            type="number"
            min="0"
            [max]="maxDays"
            [value]="warningDays()"
            (input)="warningDays.set(number($event))"
            class="w-20 rounded-lg border border-gray-200 bg-white px-2.5 py-1.5 text-sm font-semibold text-gray-900 tabular-nums outline-none focus:border-moza-400 focus:ring-2 focus:ring-moza-100"
          />
        </label>

        @if (problem(); as message) {
          <p class="mt-2.5 rounded-lg bg-alert-50 px-3 py-2 text-xs text-alert-700">
            {{ message }}
          </p>
        }

        <div class="mt-4 flex items-center justify-between gap-3">
          @if (settings().updatedBy; as who) {
            <p class="min-w-0 truncate text-2xs text-gray-400">
              {{ who }}
              @if (settings().updatedAt; as when) {
                · {{ date(when) }}
              }
            </p>
          } @else {
            <span></span>
          }

          <button
            type="button"
            (click)="save()"
            [disabled]="problem() !== null || !changed()"
            class="shrink-0 rounded-xl bg-moza-700 px-3.5 py-2 text-sm font-semibold text-white transition-colors hover:bg-moza-800 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Guardar
          </button>
        </div>
      </div>
    }
  `,
})
export class SlaSettingsPopoverComponent {
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);

  readonly settings = input.required<SlaSettings>();
  readonly save_ = output<{ caseSlaDays: number; caseWarningDays: number }>({ alias: 'saved' });

  protected readonly maxDays = MAX_SLA_DAYS;
  protected readonly open = signal(false);
  protected readonly slaDays = signal(0);
  protected readonly warningDays = signal(0);

  constructor() {
    // Enquanto o popover está fechado, os campos seguem o que veio do servidor;
    // aberto, é o que o operador escreveu que manda, até guardar ou desistir.
    effect(() => {
      const settings = this.settings();
      if (this.open()) return;
      this.slaDays.set(settings.caseSlaDays);
      this.warningDays.set(settings.caseWarningDays);
    });
  }

  protected readonly changed = computed(
    () =>
      this.slaDays() !== this.settings().caseSlaDays ||
      this.warningDays() !== this.settings().caseWarningDays,
  );

  protected readonly problem = computed<string | null>(() => {
    const sla = this.slaDays();
    const warning = this.warningDays();
    if (!Number.isInteger(sla) || sla < 1 || sla > MAX_SLA_DAYS) {
      return `O prazo tem de estar entre 1 e ${MAX_SLA_DAYS} dias.`;
    }
    if (!Number.isInteger(warning) || warning < 0) {
      return 'O aviso não pode ser um número negativo de dias.';
    }
    if (warning >= sla) return 'O aviso tem de ser menor do que o prazo.';
    return null;
  });

  protected toggle(): void {
    this.open.set(!this.open());
  }

  protected save(): void {
    if (this.problem() !== null) return;
    this.save_.emit({ caseSlaDays: this.slaDays(), caseWarningDays: this.warningDays() });
    this.open.set(false);
  }

  protected onDocumentMouseDown(event: MouseEvent): void {
    if (!this.open()) return;
    if (!this.host.nativeElement.contains(event.target as Node)) this.open.set(false);
  }

  protected number = (event: Event) => Number((event.target as HTMLInputElement).value);
  protected date = formatDate;
}
