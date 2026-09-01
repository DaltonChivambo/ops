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
 * Cartão de gráfico que encolhe para o cabeçalho.
 *
 * Numa execução com dezoito mil fechos, a tabela é o que se vem cá ver — quem
 * já sabe como está o apuramento quer fechar os gráficos e ganhar o ecrã. A
 * escolha guarda-se, senão fechá-los a cada visita era mais trabalho do que
 * rolar por eles.
 *
 * `@container` fica sempre ligado: o conteúdo destes cartões precisa de saber a
 * largura do cartão, não a da janela. Atenção ao usar isto noutro sítio — o
 * `container-type` faz do cartão bloco de contenção para descendentes `fixed`.
 */
@Component({
  selector: 'app-collapsible-card',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CardComponent, LucideChevronDown],
  host: {
    class: 'block',
    // Aberto, estica para igualar o cartão ao lado. Fechado, encolhe para o
    // cabeçalho — senão ficava um cartão vazio da altura do vizinho.
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
   * `heading` e não `title`: `title` é um atributo global do HTML, e quem usasse
   * o componente com atributo estático — `<app-collapsible-card title="...">` —
   * deixava-o no DOM além de o passar como input. O browser fazia dele tooltip
   * do cartão inteiro, e passar o rato por um gráfico mostrava um balão a
   * repetir o cabeçalho que já lá está escrito.
   */
  readonly heading = input.required<string>();
  /** Sufixo da chave em localStorage. Sem ele, o estado não sobrevive à navegação. */
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
