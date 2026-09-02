import { ChangeDetectionStrategy, Component, input, signal } from '@angular/core';
import { LucideChevronDown } from '@lucide/angular';

import { CardComponent } from './card';

const STORAGE_PREFIX = 'mozaops.card.';

/** O que ficou fechado fica fechado — entre navegações e entre sessões. */
function readStored(key: string): boolean | null {
  try {
    const raw = localStorage.getItem(STORAGE_PREFIX + key);
    return raw === null ? null : raw === 'open';
  } catch {
    // Modo privado, cookies bloqueados: não é motivo para o cartão não abrir.
    return null;
  }
}

function writeStored(key: string, open: boolean): void {
  try {
    localStorage.setItem(STORAGE_PREFIX + key, open ? 'open' : 'closed');
  } catch {
    /* idem */
  }
}

/**
 * Cartão de gráfico que encolhe para o cabeçalho, e lembra-se da escolha.
 *
 * `@container` fica sempre ligado, para o conteúdo se medir pelo cartão e não
 * pela janela. Atenção: `container-type` faz dele bloco de contenção para
 * descendentes `fixed`.
 */
@Component({
  selector: 'app-collapsible-card',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CardComponent, LucideChevronDown],
  host: {
    class: 'block',
    // Aberto, iguala o cartão ao lado; fechado, encolhe para o cabeçalho.
    '[class.h-full]': 'open()',
    '[class.self-start]': '!open()',
  },
  template: `
    <section appCard class="@container flex h-full flex-col gap-4">
      <div class="flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
        <button
          type="button"
          (click)="toggle()"
          [attr.aria-expanded]="open()"
          [attr.aria-label]="(open() ? 'Encolher' : 'Expandir') + ': ' + heading()"
          class="-m-1.5 flex items-center gap-2 rounded-lg p-1.5 transition-colors hover:bg-gray-50 focus-visible:bg-gray-50 focus-visible:outline-none"
        >
          <svg
            lucideChevronDown
            [size]="18"
            [strokeWidth]="2.2"
            class="shrink-0 text-gray-400 transition-transform duration-200"
            [class.-rotate-90]="!open()"
          ></svg>
          <h2 class="text-lg font-bold">{{ heading() }}</h2>
        </button>

        <!-- Fica à vista mesmo fechado: é o que diz o que o cartão contém. -->
        <ng-content select="[cardAside]" />
      </div>

      <div class="flex flex-1 flex-col" [class.hidden]="!open()">
        <ng-content />
      </div>
    </section>
  `,
})
export class CollapsibleCardComponent {
  /**
   * `heading` e não `title`: `title` é atributo global do HTML, e em uso
   * estático fica no DOM, virando tooltip do cartão inteiro.
   */
  readonly heading = input.required<string>();
  /** Sufixo da chave em localStorage. */
  readonly storageKey = input.required<string>();

  protected readonly open = signal(true);
  private restored = false;

  protected toggle(): void {
    this.ensureRestored();
    const next = !this.open();
    this.open.set(next);
    writeStored(this.storageKey(), next);
  }

  constructor() {
    queueMicrotask(() => this.ensureRestored());
  }

  /** Lê-se uma vez, e só depois de o input estar preenchido. */
  private ensureRestored(): void {
    if (this.restored) return;
    this.restored = true;
    const stored = readStored(this.storageKey());
    if (stored !== null) this.open.set(stored);
  }
}
