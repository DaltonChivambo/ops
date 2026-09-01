import { ChangeDetectionStrategy, Component, inject } from '@angular/core';

import { ROLE_LABELS } from '../../core/auth/roles';
import { SessionStore } from '../../core/auth/session.store';
import { HeaderComponent } from '../../layout/header';

/**
 * Autenticado, mas sem o papel necessário.
 *
 * Distinto de «não autenticado»: mandar esta pessoa de volta ao Keycloak não
 * resolveria nada — entraria com os mesmos papéis e voltaria aqui. O que ela
 * precisa de saber é a quem pedir.
 */
@Component({
  selector: 'app-forbidden-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [HeaderComponent],
  template: `
    <app-header heading="Sem permissão" />

    <div class="grid grow place-items-center p-6">
      <div class="max-w-md rounded-lg border border-alert-100 bg-white p-8 text-center">
        <span
          class="grid size-11 place-items-center rounded-full bg-alert-50 text-xl text-alert-600 mx-auto"
        >
          !
        </span>
        <h2 class="mt-4 font-semibold text-moza-800">Não tem acesso a esta área</h2>
        <p class="mt-2 text-sm leading-relaxed text-moza-500">
          A sua conta está autenticada, mas o papel atribuído não permite abrir esta página.
        </p>
        <p class="mt-4 text-sm text-moza-500">
          Papel actual: <span class="font-medium text-moza-700">{{ roles() }}</span>
        </p>
        <p class="mt-4 text-xs text-moza-400">
          Os papéis são atribuídos pelos grupos do directório. Fale com a coordenação do DOP.
        </p>
      </div>
    </div>
  `,
})
export class ForbiddenPageComponent {
  private readonly session = inject(SessionStore);

  roles(): string {
    const roles = this.session.roles();
    return roles.length ? roles.map((role) => ROLE_LABELS[role]).join(' · ') : 'nenhum';
  }
}
