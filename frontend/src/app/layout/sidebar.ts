import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  model,
  signal,
  type Signal,
} from '@angular/core';
import { NgTemplateOutlet } from '@angular/common';
// Renomeado: a classe também tem um método isActive.
import { isActive as routeIsActive, Router } from '@angular/router';
import {
  LucideBanknote,
  LucideChevronDown,
  LucideChevronRight,
  LucideChevronsLeft,
  LucideChevronsRight,
  LucideLayoutGrid,
  LucideMonitorSmartphone,
  LucideShieldAlert,
  LucideX,
} from '@lucide/angular';

import { findModule } from '../core/navigation';
import { ChannelFlyoutComponent } from './channel-flyout';
import { UserMenuComponent } from './user-menu';

/** Um dos ícones que a barra sabe desenhar. O `@switch` traduz para o componente. */
type NavIcon = 'layout-grid' | 'monitor-smartphone' | 'banknote' | 'shield-alert';

interface NavChild {
  readonly id: string;
  readonly label: string;
  /** Presente só quando a página existe; sem isto o item não navega. */
  readonly route?: string;
  /** Canais abrem o painel lateral de funcionalidades em vez de navegar já. */
  readonly channel?: boolean;
}

interface NavItem {
  readonly id: string;
  readonly label: string;
  readonly icon: NavIcon;
  readonly route?: string;
  readonly children?: readonly NavChild[];
}

interface NavSection {
  readonly id: string;
  readonly label?: string;
  readonly items: readonly NavItem[];
}

const SECTIONS: readonly NavSection[] = [
  {
    id: 'geral',
    items: [{ id: 'dashboard', label: 'Dashboard', icon: 'layout-grid', route: '/dashboard' }],
  },
  {
    id: 'mpc',
    label: 'Meios de Pag. e Canais',
    items: [
      {
        id: 'canais',
        label: 'Canais',
        icon: 'monitor-smartphone',
        children: [
          { id: 'pos', label: 'POS', route: '/pos', channel: true },
          { id: 'atm', label: 'ATM', route: '/atm', channel: true },
          { id: 'kiosks', label: 'Quiosques', route: '/kiosks', channel: true },
        ],
      },
      {
        id: 'pagamentos',
        label: 'Pagamentos',
        icon: 'banknote',
        children: [
          { id: 'salarios', label: 'Proc. de Salários' },
          { id: 'cartoes', label: 'Cartões' },
          { id: 'cheques', label: 'Cheques' },
        ],
      },
      {
        // id mantém o nome completo da ilha (ver README do departamento);
        // o label é curto de propósito — a barra lateral não tem largura
        // para "Suporte e Monitorização de Fraudes".
        id: 'suporte-fraudes',
        label: 'Fraudes',
        icon: 'shield-alert',
      },
    ],
  },
];

/** O activo lê-se do URL (não de estado local) — é o que dá deep links e o botão «voltar». */
@Component({
  selector: 'app-sidebar',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    NgTemplateOutlet,
    ChannelFlyoutComponent,
    LucideBanknote,
    LucideChevronDown,
    LucideChevronRight,
    LucideChevronsLeft,
    LucideChevronsRight,
    LucideLayoutGrid,
    LucideMonitorSmartphone,
    LucideShieldAlert,
    LucideX,
    UserMenuComponent,
  ],
  template: `
    @if (open()) {
      <div
        class="fixed inset-0 z-30 bg-gray-900/40 lg:hidden"
        aria-hidden="true"
        (click)="open.set(false)"
      ></div>
    }

    <aside
      class="fixed inset-y-0 left-0 z-40 flex flex-col border-r border-gray-100 bg-white py-6 transition-[width,translate] duration-200 lg:translate-x-0"
      [class]="collapsed() ? 'w-[4.75rem] px-3' : 'w-[16.5rem] px-4'"
      [class.translate-x-0]="open()"
      [class.-translate-x-full]="!open()"
    >
      <button
        type="button"
        (click)="toggleCollapse()"
        [attr.aria-label]="collapsed() ? 'Expandir menu' : 'Encolher menu'"
        [attr.aria-expanded]="!collapsed()"
        class="absolute top-8 -right-3.5 z-10 hidden size-7 items-center justify-center rounded-full border border-gray-200 bg-white text-gray-500 shadow-md transition-colors hover:border-moza-200 hover:bg-moza-50 hover:text-moza-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-moza-400 lg:inline-flex"
      >
        @if (collapsed()) {
          <svg lucideChevronsRight [size]="15" [strokeWidth]="2.2"></svg>
        } @else {
          <svg lucideChevronsLeft [size]="15" [strokeWidth]="2.2"></svg>
        }
      </button>

      <div class="mb-6 flex items-center" [class]="collapsed() ? 'justify-center' : 'gap-3 px-3'">
        @if (collapsed()) {
          <img src="mozaops_logo_OPS_sem_fundo.svg" alt="MozaOps" class="h-5 w-auto" />
        } @else {
          <span class="min-w-0">
            <img src="mozaops_logo_sem_fundo.svg" alt="MozaOps" class="h-8 w-auto" />
            <!-- Duas linhas em vez de truncar: cortado, o nome do departamento
                 deixa de dizer de qual se trata. -->
            <span class="mt-1.5 block text-2xs leading-snug text-gray-400">
              Meios de Pagamentos e Canais
            </span>
          </span>
          <button
            type="button"
            class="ml-auto inline-flex size-8 shrink-0 items-center justify-center rounded-full text-gray-600 hover:bg-moza-50 lg:hidden"
            aria-label="Fechar menu"
            (click)="open.set(false)"
          >
            <svg lucideX [size]="20" [strokeWidth]="1.8"></svg>
          </button>
        }
      </div>

      <nav class="thin-scrollbar min-h-0 flex-1 overflow-y-auto" aria-label="Principal">
        @for (section of sections; track section.id; let sectionIndex = $index) {
          <div>
            @if (section.label && !collapsed()) {
              <p
                class="mt-6 mb-2 px-3 text-2xs font-semibold tracking-wider text-gray-400 uppercase"
              >
                {{ section.label }}
              </p>
            }
            @if (collapsed() && sectionIndex > 0) {
              <hr class="my-3 border-gray-100" />
            }

            <ul class="flex flex-col gap-1">
              @for (item of section.items; track item.id) {
                <ng-container
                  [ngTemplateOutlet]="navItem"
                  [ngTemplateOutletContext]="{ $implicit: item }"
                />
              }
            </ul>
          </div>
        }
      </nav>

      <div class="mt-4 border-t border-gray-100 pt-4">
        <app-user-menu [collapsed]="collapsed()" />
      </div>
    </aside>

    @if (flyoutModule(); as mod) {
      <app-channel-flyout
        [module]="mod"
        [collapsed]="collapsed()"
        (closed)="flyoutChannelId.set(null)"
        (selected)="onFlyoutSelect()"
      />
    }

    <!-- Um item da barra: o botão, e a sublista quando o grupo está aberto. -->
    <ng-template #navItem let-item>
      <li>
        <button
          type="button"
          [attr.aria-current]="isActive(item) ? 'page' : null"
          [attr.aria-expanded]="item.children ? isExpanded(item.id) : null"
          [attr.aria-label]="item.label"
          [attr.title]="collapsed() ? item.label : null"
          (click)="onItemClick(item)"
          class="relative flex w-full items-center gap-3 rounded-xl py-2.5 text-left text-base transition-colors"
          [class]="collapsed() ? 'justify-center px-0' : 'px-3'"
          [class.bg-moza-100]="isActive(item)"
          [class.font-semibold]="isActive(item)"
          [class.text-moza-700]="isActive(item) || hasActiveChild(item)"
          [class.font-medium]="!isActive(item) && hasActiveChild(item)"
          [class.hover:bg-moza-50]="!isActive(item)"
          [class.text-gray-600]="!isActive(item) && !hasActiveChild(item)"
          [class.hover:text-gray-900]="!isActive(item) && !hasActiveChild(item)"
        >
          @if (isActive(item)) {
            <span
              class="absolute inset-y-1.5 left-0 w-1 rounded-full bg-alert-500"
              aria-hidden="true"
            ></span>
          }

          <!-- Ícone a vermelho onde se está: no item que é a página, e no grupo
               que a contém. É a única pista com a barra encolhida. A régua e o
               fundo ficam só no primeiro — um grupo não é uma página. -->
          <span class="shrink-0" [class.text-alert-500]="isActive(item) || hasActiveChild(item)">
            @switch (item.icon) {
              @case ('layout-grid') {
                <svg lucideLayoutGrid [size]="20" [strokeWidth]="1.8"></svg>
              }
              @case ('monitor-smartphone') {
                <svg lucideMonitorSmartphone [size]="20" [strokeWidth]="1.8"></svg>
              }
              @case ('banknote') {
                <svg lucideBanknote [size]="20" [strokeWidth]="1.8"></svg>
              }
              @case ('shield-alert') {
                <svg lucideShieldAlert [size]="20" [strokeWidth]="1.8"></svg>
              }
            }
          </span>

          @if (!collapsed()) {
            <span class="min-w-0 flex-1 truncate">{{ item.label }}</span>
          }

          @if (!collapsed() && item.children) {
            <svg
              lucideChevronDown
              [size]="16"
              [strokeWidth]="1.8"
              class="shrink-0 text-gray-400 transition-transform"
              [class.rotate-180]="isExpanded(item.id)"
            ></svg>
          }
        </button>

        @if (item.children && isExpanded(item.id) && !collapsed()) {
          <ul
            class="mt-1 mb-1.5 ml-[1.4375rem] flex flex-col gap-0.5 border-l border-moza-100 pl-3"
          >
            @for (child of item.children; track child.id) {
              <li>
                <button
                  type="button"
                  [attr.aria-current]="isChildActive(child) ? 'page' : null"
                  [attr.aria-haspopup]="child.channel ? 'menu' : null"
                  [attr.aria-expanded]="child.channel ? flyoutChannelId() === child.id : null"
                  (click)="onChildClick(child)"
                  class="relative flex w-full items-center gap-1 rounded-lg px-3 py-2 text-left text-sm transition-colors"
                  [class.bg-moza-100]="isChildActive(child)"
                  [class.font-semibold]="isChildActive(child)"
                  [class.text-moza-700]="isChildActive(child)"
                  [class.text-gray-500]="!isChildActive(child)"
                  [class.hover:bg-moza-50]="!isChildActive(child)"
                  [class.hover:text-gray-900]="!isChildActive(child)"
                >
                  @if (isChildActive(child)) {
                    <span
                      class="absolute inset-y-1 left-0 w-0.5 rounded-full bg-alert-500"
                      aria-hidden="true"
                    ></span>
                  }
                  <span class="min-w-0 flex-1 truncate">{{ child.label }}</span>
                  @if (child.channel) {
                    <svg
                      lucideChevronRight
                      [size]="15"
                      [strokeWidth]="1.8"
                      class="shrink-0 text-gray-400"
                    ></svg>
                  }
                </button>
              </li>
            }
          </ul>
        }
      </li>
    </ng-template>
  `,
})
export class SidebarComponent {
  private readonly router = inject(Router);

  /** `model` porque a shell também os mexe: encolher desloca o conteúdo. */
  readonly collapsed = model(false);
  readonly open = model(false);

  protected readonly sections = SECTIONS;

  /** Canais aberto por omissão: é o único grupo com páginas construídas. */
  protected readonly expandedIds = signal<ReadonlySet<string>>(new Set(['canais']));
  protected readonly flyoutChannelId = signal<string | null>(null);

  protected readonly flyoutModule = computed(() => {
    const id = this.flyoutChannelId();
    return id ? (findModule(id) ?? null) : null;
  });

  protected isExpanded(id: string): boolean {
    return this.expandedIds().has(id);
  }

  /**
   * Um sinal por rota, construído uma vez — as rotas da barra são estáticas.
   *
   * Tem de ser sinal: `router.url` é uma propriedade, e com OnPush sem zone.js
   * mudar de página não avisava a barra, que só se marcava ao clique seguinte.
   */
  private readonly activeByRoute = new Map<string, Signal<boolean>>();

  constructor() {
    const registar = (route?: string) => {
      if (route && !this.activeByRoute.has(route)) {
        this.activeByRoute.set(route, routeIsActive(route, this.router));
      }
    };
    for (const section of SECTIONS) {
      for (const item of section.items) {
        registar(item.route);
        for (const child of item.children ?? []) registar(child.route);
      }
    }
  }

  protected isActive(item: NavItem): boolean {
    return this.activeByRoute.get(item.route ?? '')?.() ?? false;
  }

  protected isChildActive(child: NavChild): boolean {
    return this.activeByRoute.get(child.route ?? '')?.() ?? false;
  }

  protected hasActiveChild(item: NavItem): boolean {
    return item.children?.some((child) => this.isChildActive(child)) ?? false;
  }

  protected toggleCollapse(): void {
    this.flyoutChannelId.set(null);
    this.collapsed.update((value) => !value);
  }

  protected onItemClick(item: NavItem): void {
    if (item.children) {
      this.toggleGroup(item.id);
      return;
    }
    if (item.route) {
      this.flyoutChannelId.set(null);
      void this.router.navigateByUrl(item.route);
      this.open.set(false);
    }
  }

  protected onChildClick(child: NavChild): void {
    if (child.channel) {
      this.flyoutChannelId.update((current) => (current === child.id ? null : child.id));
      return;
    }
    if (child.route) {
      this.flyoutChannelId.set(null);
      void this.router.navigateByUrl(child.route);
      this.open.set(false);
    }
  }

  protected onFlyoutSelect(): void {
    this.flyoutChannelId.set(null);
    this.open.set(false);
  }

  private toggleGroup(id: string): void {
    if (this.collapsed()) {
      // Num sidebar só de ícones não há onde mostrar os módulos: expandir primeiro.
      this.collapsed.set(false);
      this.expandedIds.update((current) => new Set(current).add(id));
      return;
    }
    this.expandedIds.update((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }
}
