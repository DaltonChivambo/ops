import { ChangeDetectionStrategy, Component, signal } from '@angular/core';
import { RouterOutlet } from '@angular/router';

import { SidebarComponent } from './sidebar';

/**
 * Abaixo disto a barra arranca encolhida por omissão — portáteis e ecrãs mais
 * pequenos, onde os 16.5rem da barra expandida comem uma fatia grande do
 * ecrã antes de o utilizador tocar em nada. É só o valor inicial: continua a
 * poder expandir-se a qualquer momento.
 */
const COLLAPSE_BELOW_PX = 1536;

/**
 * A casca, copiada de `client/src/app/App.tsx`.
 *
 * A barra é `fixed` e não participa no fluxo; é a margem esquerda do `main` que
 * lhe abre lugar, e é por isso que ela precisa de acompanhar o estado encolhido.
 * O fundo `#f7f6fb` vem do v1 tal como está — não é um cinzento do Tailwind.
 */
@Component({
  selector: 'app-shell',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterOutlet, SidebarComponent],
  template: `
    <div class="min-h-screen bg-[#f7f6fb] text-gray-900">
      <app-sidebar [(collapsed)]="collapsed" [(open)]="open" />

      <!-- O atributo data-sidebar publica o estado da barra para o conteúdo. Os media
           queries só sabem a largura da JANELA, mas o espaço que as páginas têm
           depende também da barra: a 1280px sobram 1140px com ela encolhida e
           só 952px com ela aberta. Sem isto, abrir a barra apertava a página
           sem que nenhum breakpoint desse por isso. -->
      <main
        class="group/shell px-4 py-5 transition-[margin] duration-200 sm:px-6 lg:px-8 lg:py-6"
        [attr.data-sidebar]="collapsed() ? 'collapsed' : 'expanded'"
        [class]="collapsed() ? 'lg:ml-[4.75rem]' : 'lg:ml-[16.5rem]'"
      >
        <router-outlet />
      </main>
    </div>
  `,
})
export class ShellComponent {
  protected readonly collapsed = signal(
    typeof window !== 'undefined' ? window.innerWidth < COLLAPSE_BELOW_PX : false,
  );
  /** Só conta abaixo de `lg`: aí a barra desliza por cima em vez de empurrar. */
  protected readonly open = signal(false);
}
