import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { LucideInfo, LucideShieldCheck } from '@lucide/angular';

/** Identifica a automação. Sem isto a página abria directamente num formulário. */
@Component({
  selector: 'app-page-title',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [LucideInfo, LucideShieldCheck],
  template: `
    <div class="flex items-start gap-3.5">
      <span
        class="inline-flex size-11 shrink-0 items-center justify-center rounded-xl bg-moza-700 text-white"
      >
        <svg lucideShieldCheck [size]="22" [strokeWidth]="1.8"></svg>
      </span>

      <div class="min-w-0">
        <div class="flex items-center gap-1.5">
          <h1 class="text-xl leading-tight font-bold text-gray-900">{{ title() }}</h1>

          <!-- A descrição é longa; fica arrumada num "i" e só aparece a pedido. -->
          <span class="group relative inline-flex">
            <button
              type="button"
              aria-label="Sobre esta funcionalidade"
              class="inline-flex size-6 items-center justify-center rounded-full text-gray-400 transition-colors hover:bg-moza-50 hover:text-moza-700 focus-visible:bg-moza-50 focus-visible:text-moza-700 focus-visible:outline-none"
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
      </div>
    </div>
  `,
})
export class PageTitleComponent {
  readonly title = input.required<string>();
  readonly description = input.required<string>();
}
