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

/**
 * As classes da própria `<table>` e do seu `<thead>`.
 *
 * Ficam aqui e não dentro do componente porque a tabela é de quem a usa — é lá
 * que estão as colunas, e não há forma de as adivinhar. Partilha-se o aspecto,
 * como nos STATE_CHIP e no AVATAR_CLASS, para as tabelas não divergirem umas
 * das outras à primeira alteração.
 *
 * A largura mínima é de cada uma: depende de quantas colunas tem.
 */
export const TABLE_CLASS = 'w-full border-collapse text-sm';

/** Colado ao topo da caixa. O fundo vai nas células, nunca aqui — ver o data-table. */
export const THEAD_CLASS = 'sticky top-0 z-10';

/**
 * O invólucro de uma lista longa: cartão, barra de filtros colada, caixa com
 * scroll próprio, scroll infinito e rodapé.
 *
 * Nasceu de duas tabelas que eram a mesma coisa por fora — a dos fechos e a dos
 * casos — e diferentes só nas colunas. Tudo o que aqui está tinha sido resolvido
 * uma vez em cada uma, com os mesmos números mágicos copiados, e cada correcção
 * era duas correcções (ou uma, e um bug no ficheiro esquecido).
 *
 * O que fica de fora, de propósito: as colunas e as linhas. Projectam-se, o que
 * significa que quem usa mantém controlo total sobre as células — as linhas
 * agrupadas e expansíveis dos fechos continuam possíveis, e uma automação nova
 * não fica presa ao formato «uma linha por registo».
 *
 * O que se ganha por usar:
 * - cartão e barra de filtros colada por baixo dos separadores;
 * - caixa com a altura certa (ver a nota do max-h) e o scroll da página primeiro;
 * - scroll infinito com sentinela, sem repetir o IntersectionObserver;
 * - a lista esbatida enquanto carrega, em vez de saltar;
 * - «a carregar mais», «fim da lista» e o botão de voltar ao topo.
 */
@Component({
  selector: 'app-data-table',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [PageFirstScrollDirective, LucideArrowUp, LucideLoaderCircle],
  template: `
    <!-- Sem overflow-hidden: cortaria os painéis que os filtros abrem quando a
         tabela é curta. E o cartão é o contentor de consultas, para as colunas
         poderem esconder-se pela largura DELE e não pela da janela. -->
    <div class="@container rounded-2xl border border-gray-100 bg-white shadow-sm">
      <!-- Cola por baixo dos separadores: os filtros e a pesquisa são o que mais
           se mexe enquanto se percorre a lista, e saíam do ecrã logo à primeira.

           z-20 e não z-10: a barra cria contexto de empilhamento, portanto tudo
           o que está dentro dela — os painéis que os filtros abrem — fica preso a
           este nível. Empatada a 10 com o cabeçalho da tabela, decidia a ordem no
           DOM e o cabeçalho ganhava, tapando o que se abrisse aqui. -->
      <div
        class="sticky top-[calc(var(--app-header-h)+var(--tabs-h))] z-20 flex flex-wrap items-center gap-2.5 rounded-t-2xl border-b border-gray-100 bg-white px-4 py-3.5 sm:px-5"
      >
        <ng-content select="[toolbar]" />
      </div>

      <!-- O limite de altura conta com o que divide o ecrã com a lista, e não é
           um número à parte: se o cartão for mais alto do que o que sobra, no fim
           do scroll da página ele passa por baixo da barra de filtros colada e ela
           come o topo do cabeçalho da tabela. Daí descontar, além do que a barra
           ocupa (~70px), do rodapé (~60px) e da margem inferior da página (~13px),
           também os desvios onde ela própria cola — assim a conta continua certa
           abaixo do lg, onde a barra do menu existe e o desvio quase duplica.

           E min-h para a caixa não desabar quando um filtro deixa três linhas: a
           página encurtava, o scroll era puxado para cima e perdia-se o sítio.
           relative é bloco de contenção — sem ele um descendente absolute escapa
           ao recorte e estica a altura da PÁGINA à da tabela. -->
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

        <!-- Escape para quem não quer rolar milhares de linhas para voltar ao
             princípio. Rola a LISTA, não a página — quem quer a página tem o
             botão na barra dos separadores. -->
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
  /** Onde o scroll da página assenta antes de a lista correr — os separadores. */
  readonly scrollAnchor = input<HTMLElement | undefined>(undefined);

  /** A primeira página está a chegar: esbate a lista em vez de a esvaziar. */
  readonly loading = input(false);
  /** Uma página seguinte está a chegar. */
  readonly loadingMore = input(false);
  /** Ainda há páginas por pedir; a falso e com linhas, mostra «fim da lista». */
  readonly hasMore = input(false);
  /** Distingue a lista vazia da lista completa — só a segunda tem fim a anunciar. */
  readonly hasRows = input(false);
  /** O botão de voltar ao princípio da lista; só vale a pena com linhas que cheguem. */
  readonly backToTop = input(false);

  /** A sentinela entrou no ecrã: peça a página seguinte. */
  readonly loadMore = output<void>();

  private readonly scrollBox = viewChild.required<ElementRef<HTMLElement>>('scrollBox');
  private readonly sentinel = viewChild.required<ElementRef<HTMLElement>>('sentinel');

  constructor() {
    // Observa a sentinela só quando faz sentido pedir mais. `hasRows` evita pedir
    // a página 2 antes de a 1 chegar, quando um filtro esvazia a lista.
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

  /** Devolve a lista ao princípio — usado pelo botão e por quem troca de consulta. */
  scrollToTop(behavior: ScrollBehavior = 'smooth'): void {
    this.scrollBox().nativeElement.scrollTo({ top: 0, behavior });
  }
}
