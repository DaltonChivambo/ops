import { ChangeDetectionStrategy, Component, signal } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { LucideMenu } from '@lucide/angular';

import { SidebarComponent } from './sidebar';

/** Abaixo disto a barra arranca encolhida. É só o valor inicial. */
const COLLAPSE_BELOW_PX = 1536;

/**
 * A casca da aplicação.
 *
 * A barra é `fixed` e não participa no fluxo: é a margem esquerda do `main` que
 * lhe abre lugar, e por isso tem de acompanhar o estado encolhido.
 */
@Component({
  selector: 'app-shell',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterOutlet, SidebarComponent, LucideMenu],
  template: `
    <div class="min-h-screen bg-[#f7f6fb] text-gray-900">
      <app-sidebar [(collapsed)]="collapsed" [(open)]="open" />

      <!-- Abaixo do lg a barra lateral sai do ecrã e passa a deslizar por cima.
           Até aqui não havia de onde a trazer de volta: cinco sítios fechavam-na
           e nenhum a abria, portanto num portátil estreito a navegação ficava
           inalcançável. Esta barra existe só para isso.
           z-20 e não z-30: quando o menu abre, o véu tem de a cobrir também. -->
      <header
        class="sticky top-0 z-20 flex items-center gap-2 border-b border-gray-100 bg-white/95 px-4 py-2.5 backdrop-blur lg:hidden"
      >
        <button
          type="button"
          (click)="openMenu()"
          aria-label="Abrir menu de navegação"
          class="inline-flex size-9 shrink-0 items-center justify-center rounded-lg text-gray-600 transition-colors hover:bg-moza-50 hover:text-moza-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-moza-400"
        >
          <svg lucideMenu [size]="20" [strokeWidth]="1.8"></svg>
        </button>
        <img src="mozaops_logo_sem_fundo.svg" alt="MozaOps" class="h-6 w-auto" />
      </header>

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

  /**
   * Num ecrã estreito abre sempre por extenso: encolhida é uma coluna de ícones
   * sem rótulos, e o botão de fechar só existe no estado expandido.
   */
  protected openMenu(): void {
    this.collapsed.set(false);
    this.open.set(true);
  }
}
