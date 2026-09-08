import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';

import { SessionStore } from '../../core/auth/session.store';
import { areaLabel } from '../../core/navigation';
import { HeaderComponent } from '../../layout/header';

/**
 * Autenticado, mas fora da área a que a página pertence.
 *
 * Distinto de «não autenticado»: mandar esta pessoa entrar de novo não
 * resolveria nada — voltaria com as mesmas áreas e cairia aqui outra vez. O
 * que ela precisa de saber é a quem pedir, e com que unidade orgânica está
 * registada no GEEA — que é o que a coordenação vai perguntar.
 */
@Component({
  selector: 'app-forbidden-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [HeaderComponent],
  template: `
    <app-header heading="Sem acesso" />

    <div class="grid grow place-items-center p-6">
      <div class="max-w-md rounded-lg border border-alert-100 bg-white p-8 text-center">
        <span
          class="grid size-11 place-items-center rounded-full bg-alert-50 text-xl text-alert-600 mx-auto"
        >
          !
        </span>
        <h2 class="mt-4 font-semibold text-moza-800">Não tem acesso a esta área</h2>
        <p class="mt-2 text-sm leading-relaxed text-moza-500">
          A sua conta está autenticada, mas esta página é de uma área a que não pertence.
        </p>
        <p class="mt-4 text-sm text-moza-500">
          As suas áreas: <span class="font-medium text-moza-700">{{ areas() }}</span>
        </p>
        <p class="mt-1 text-sm text-moza-500">
          Registado em: <span class="font-medium text-moza-700">{{ unidade() }}</span>
        </p>
        <p class="mt-4 text-xs text-moza-400">
          O acesso vem da unidade orgânica registada no GEEA. Fale com a coordenação do DOP.
        </p>
      </div>
    </div>
  `,
})
export class ForbiddenPageComponent {
  private readonly session = inject(SessionStore);

  /** O id cru quando o catálogo não conhece a área: dizer o id é mais útil a
      quem der o apoio do que não dizer nada. */
  protected readonly areas = computed(() => {
    const areas = this.session.areas();
    return areas.length ? areas.map((area) => areaLabel(area) ?? area).join(' · ') : 'nenhuma';
  });

  protected readonly unidade = computed(() => {
    const principal = this.session.principal();
    if (!principal?.department) return '—';
    return `${principal.department} (${principal.departmentCode})`;
  });
}
