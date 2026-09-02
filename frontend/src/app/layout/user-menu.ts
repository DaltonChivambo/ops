import {
  ChangeDetectionStrategy,
  Component,
  computed,
  ElementRef,
  inject,
  input,
  signal,
} from '@angular/core';
import {
  LucideChevronsUpDown,
  LucideKeyRound,
  LucideLifeBuoy,
  LucideLogOut,
  LucideSettings,
  LucideUser,
} from '@lucide/angular';

import { ROLE_LABELS, type Role } from '../core/auth/roles';
import { SessionStore } from '../core/auth/session.store';
import { AVATAR_CLASS } from '../shared/ui/avatar';

/**
 * Entradas por construir: à vista e desactivadas, em vez de clicáveis e sem
 * efeito. Quem é dono da identidade é o Keycloak, não esta aplicação, portanto
 * o destino provável é a consola de conta dele.
 */
const SOON_ITEMS = [
  { id: 'profile', label: 'Perfil', icon: 'user' },
  { id: 'password', label: 'Alterar palavra-passe', icon: 'key' },
  { id: 'settings', label: 'Definições', icon: 'settings' },
  { id: 'support', label: 'Suporte', icon: 'life-buoy' },
] as const;

/** Quem está a usar a aplicação, e o que pode fazer com a própria conta. */
@Component({
  selector: 'app-user-menu',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    LucideChevronsUpDown,
    LucideKeyRound,
    LucideLifeBuoy,
    LucideLogOut,
    LucideSettings,
    LucideUser,
  ],
  host: {
    class: 'relative block',
    '(document:mousedown)': 'onDocumentMouseDown($event)',
    '(document:keydown.escape)': 'open.set(false)',
  },
  template: `
    <button
      type="button"
      (click)="open.set(!open())"
      aria-haspopup="menu"
      [attr.aria-expanded]="open()"
      [attr.aria-label]="collapsed() ? name() : null"
      [attr.title]="collapsed() ? name() : null"
      class="flex w-full items-center rounded-xl transition-colors hover:bg-moza-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-moza-400"
      [class]="collapsed() ? 'justify-center p-1.5' : 'gap-2.5 px-2 py-2'"
    >
      <span [class]="avatarClass">{{ session.initials() }}</span>

      @if (!collapsed()) {
        <span class="min-w-0 flex-1 text-left">
          <span class="block truncate text-sm font-semibold text-gray-900">{{ name() }}</span>
          <span class="block truncate text-2xs text-gray-400">{{ roleLabels() }}</span>
        </span>
        <svg
          lucideChevronsUpDown
          [size]="14"
          [strokeWidth]="2"
          class="shrink-0 text-gray-400"
        ></svg>
      }
    </button>

    @if (open()) {
      <!-- Abre para cima: vive no fundo da barra. A w-72 é o que "Alterar
           palavra-passe" mais a etiqueta pedem sem cortar. -->
      <div
        role="menu"
        class="absolute bottom-full left-0 z-50 mb-2 w-72 rounded-xl border border-gray-100 bg-white py-1.5 shadow-lg"
      >
        @if (collapsed()) {
          <!-- Encolhida, o gatilho é só o avatar. -->
          <div class="mb-1 border-b border-gray-100 px-3 pt-1 pb-2">
            <p class="truncate text-sm font-semibold text-gray-900">{{ name() }}</p>
            <p class="truncate text-2xs text-gray-400">{{ roleLabels() }}</p>
          </div>
        }

        @for (item of soonItems; track item.id) {
          <span
            role="menuitem"
            aria-disabled="true"
            class="flex cursor-not-allowed items-center gap-2.5 px-3 py-2 text-sm text-gray-400"
          >
            @switch (item.icon) {
              @case ('user') {
                <svg lucideUser [size]="15" [strokeWidth]="1.9" class="shrink-0"></svg>
              }
              @case ('key') {
                <svg lucideKeyRound [size]="15" [strokeWidth]="1.9" class="shrink-0"></svg>
              }
              @case ('settings') {
                <svg lucideSettings [size]="15" [strokeWidth]="1.9" class="shrink-0"></svg>
              }
              @case ('life-buoy') {
                <svg lucideLifeBuoy [size]="15" [strokeWidth]="1.9" class="shrink-0"></svg>
              }
            }
            <span class="min-w-0 flex-1 truncate">{{ item.label }}</span>
            <span
              class="shrink-0 rounded-full bg-gray-100 px-1.5 py-0.5 text-2xs font-semibold text-gray-400"
            >
              em breve
            </span>
          </span>
        }

        <div class="my-1 h-px bg-gray-100"></div>

        <button
          type="button"
          role="menuitem"
          (click)="logout()"
          class="flex w-full cursor-pointer items-center gap-2.5 px-3 py-2 text-sm font-semibold text-gray-600 transition-colors hover:bg-moza-50 hover:text-gray-900"
        >
          <svg lucideLogOut [size]="15" [strokeWidth]="1.9" class="shrink-0"></svg>
          Sair
        </button>
      </div>
    }
  `,
})
export class UserMenuComponent {
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);

  protected readonly session = inject(SessionStore);
  readonly collapsed = input(false);

  protected readonly open = signal(false);
  protected readonly soonItems = SOON_ITEMS;
  protected readonly avatarClass = AVATAR_CLASS;

  protected readonly name = computed(() => this.session.principal()?.name ?? 'Sem sessão');

  protected readonly roleLabels = computed(() => {
    const roles = this.session.roles();
    if (roles.length === 0) return 'Sem papel atribuído';
    return roles.map((role: Role) => ROLE_LABELS[role]).join(' · ');
  });

  protected logout(): void {
    this.open.set(false);
    void this.session.logout();
  }

  protected onDocumentMouseDown(event: MouseEvent): void {
    if (!this.open()) return;
    if (!this.host.nativeElement.contains(event.target as Node)) this.open.set(false);
  }
}
