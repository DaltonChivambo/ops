import { ChangeDetectionStrategy, Component, inject, input } from '@angular/core';

import { ROLE_LABELS, type Role } from '../core/auth/roles';
import { SessionStore } from '../core/auth/session.store';
import { AVATAR_CLASS } from '../shared/ui/avatar';

@Component({
  selector: 'app-header',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <header
      class="flex items-center justify-between gap-4 border-b border-moza-200 bg-white px-6 py-4"
    >
      <div class="min-w-0">
        <h1 class="truncate text-lg font-semibold text-moza-800">{{ title() }}</h1>
        @if (subtitle()) {
          <p class="truncate text-sm text-moza-500">{{ subtitle() }}</p>
        }
      </div>

      <!-- O utilizador é o real, vindo do token. O MozaOps v1 tinha aqui
           «David Cooperfield / Customer» em código, porque não havia auth. -->
      <div class="flex shrink-0 items-center gap-3">
        <div class="hidden text-right sm:block">
          <p class="text-sm font-medium text-moza-800">{{ session.principal()?.name }}</p>
          <p class="text-xs text-moza-500">{{ roleLabels() }}</p>
        </div>

        <span [class]="avatarClass" [attr.aria-label]="session.principal()?.name">
          {{ session.initials() }}
        </span>

        <button
          type="button"
          class="rounded-md px-3 py-1.5 text-sm font-medium text-moza-600 transition hover:bg-moza-100 hover:text-moza-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-alert-500"
          (click)="session.logout()"
        >
          Sair
        </button>
      </div>
    </header>
  `,
})
export class HeaderComponent {
  readonly session = inject(SessionStore);

  protected readonly avatarClass = AVATAR_CLASS;

  readonly title = input.required<string>();
  readonly subtitle = input<string>('');

  roleLabels(): string {
    const roles = this.session.roles();
    if (roles.length === 0) return 'Sem papel atribuído';
    return roles.map((role: Role) => ROLE_LABELS[role]).join(' · ');
  }
}
