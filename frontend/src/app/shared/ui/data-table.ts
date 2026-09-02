import {
  ChangeDetectionStrategy,
  Component,
  effect,
  input,
  output,
  viewChild,
  type ElementRef,
} from '@angular/core';
import { LucideArrowUp, LucideLoaderCircle } from '@lucide/angular';

import { PageFirstScrollDirective } from '../page-first-scroll';

/** A largura mínima fica a cargo de quem usa: depende das colunas que tem. */
export const TABLE_CLASS = 'w-full border-collapse text-sm';

/** Colado ao topo da caixa. O fundo vai nas células, nunca aqui — ver o data-table. */
export const THEAD_CLASS = 'sticky top-0 z-10';

/**
 * Invólucro de uma lista longa: cartão, barra de filtros colada, caixa com
 * scroll próprio, scroll infinito e rodapé.
 *
 * As colunas e as linhas projectam-se, de propósito: quem usa mantém controlo
 * das células, e cabem tabelas de qualquer formato — incluindo linhas que
 * agrupam e expandem.
 */
@Component({
  selector: 'app-data-table',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [PageFirstScrollDirective, LucideArrowUp, LucideLoaderCircle],
  template: `
    <!-- Sem overflow-hidden: cortaria os painéis que os filtros abrem. O
         @container é para as colunas se esconderem pela largura do cartão. -->
    <div class="@container rounded-2xl border border-gray-100 bg-white shadow-sm">
      <!-- z-20 e não z-10: a barra cria contexto de empilhamento, e o que se
           abre dentro dela fica preso a este nível. Empatada com o cabeçalho da
           tabela, o cabeçalho ganhava e tapava os painéis dos filtros. -->
      <div
        class="sticky top-[calc(var(--app-header-h)+var(--tabs-h))] z-20 flex flex-wrap items-center gap-2.5 rounded-t-2xl border-b border-gray-100 bg-white px-4 py-3.5 sm:px-5"
      >
        <ng-content select="[toolbar]" />
      </div>

      <!-- max-h desconta os desvios onde a barra de filtros cola, além do que
           ela e o rodapé ocupam: mais alto do que isto e o cartão passa-lhe por
           baixo no fim do scroll, tapando o cabeçalho da tabela.
           min-h impede a caixa de desabar quando um filtro deixa três linhas.
           relative é bloco de contenção para o recorte. -->
      <div
        #scrollBox
        [appPageFirstScroll]="scrollAnchor()"
        class="relative max-h-[calc(100dvh-var(--app-header-h)-var(--tabs-h)-9.5rem)] min-h-[22rem] overflow-auto transition-opacity"
        [class.opacity-50]="loading()"
      >
        <ng-content />

        <!-- Sentinela do scroll infinito — fora da tabela para não sujar o tbody. -->
        <div #sentinel aria-hidden="true" class="h-px"></div>

        @if (loadingMore()) {
          <p class="flex items-center justify-center gap-2 py-4 text-sm text-gray-400">
            <svg lucideLoaderCircle [size]="15" [strokeWidth]="2" class="animate-spin"></svg>
            A carregar mais…
          </p>
        }
        @if (!hasMore() && hasRows()) {
          <p class="py-4 text-center text-sm text-gray-300">Fim da lista</p>
        }
      </div>

      <div
        class="flex flex-wrap items-center justify-between gap-3 border-t border-gray-100 px-4 py-3.5 sm:px-5"
      >
        <ng-content select="[footer]" />

        <!-- Rola a LISTA, não a página. -->
        @if (backToTop()) {
          <button
            type="button"
            (click)="scrollToTop()"
            class="ml-auto inline-flex cursor-pointer items-center gap-1.5 rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-semibold text-gray-500 transition-colors hover:bg-gray-50 hover:text-gray-900"
          >
            <svg lucideArrowUp [size]="14" [strokeWidth]="2.2"></svg>
            Voltar ao topo
          </button>
        }
      </div>
    </div>
  `,
})
export class DataTableComponent {
  /** Onde o scroll da página assenta antes de a lista correr. */
  readonly scrollAnchor = input<HTMLElement | undefined>(undefined);

  /** Esbate a lista em vez de a esvaziar enquanto a primeira página chega. */
  readonly loading = input(false);
  readonly loadingMore = input(false);
  readonly hasMore = input(false);
  /** Distingue a lista vazia da completa: só a segunda tem fim a anunciar. */
  readonly hasRows = input(false);
  readonly backToTop = input(false);

  readonly loadMore = output<void>();

  private readonly scrollBox = viewChild.required<ElementRef<HTMLElement>>('scrollBox');
  private readonly sentinel = viewChild.required<ElementRef<HTMLElement>>('sentinel');

  constructor() {
    // `hasRows` evita pedir a página 2 antes de a 1 chegar.
    effect((onCleanup) => {
      if (!this.hasMore() || this.loading() || this.loadingMore() || !this.hasRows()) return;

      const observer = new IntersectionObserver(
        (entries) => {
          if (entries[0].isIntersecting) this.loadMore.emit();
        },
        { root: this.scrollBox().nativeElement, rootMargin: '320px' },
      );
      observer.observe(this.sentinel().nativeElement);
      onCleanup(() => observer.disconnect());
    });
  }

  /** Devolve a lista ao princípio. */
  scrollToTop(behavior: ScrollBehavior = 'smooth'): void {
    this.scrollBox().nativeElement.scrollTo({ top: 0, behavior });
  }
}
