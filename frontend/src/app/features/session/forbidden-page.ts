import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { LucideLifeBuoy, LucideShieldAlert } from '@lucide/angular';

import { SessionStore } from '../../core/auth/session.store';
import { areaLabel } from '../../core/navigation';
import { HeaderComponent } from '../../layout/header';

/**
 * Autenticado, mas fora da área a que a página pertence.
 *
 * Distinto de «não autenticado»: mandar esta pessoa entrar de novo não
 * resolveria nada — voltaria com as mesmas áreas e cairia aqui outra vez. O
 * que ela precisa de saber é a quem pedir — não o mecanismo por trás (GEEA,
 * unidade orgânica, código de departamento), que não é dela e não a ajuda.
 */
@Component({
  selector: 'app-forbidden-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [HeaderComponent, LucideShieldAlert, LucideLifeBuoy],
  template: `
    <app-header heading="Sem acesso" />

    <div class="grid grow place-items-center p-6">
      <div class="w-full max-w-sm rounded-2xl border border-alert-100 bg-white p-8 text-center shadow-sm">
        <span
          class="grid size-14 place-items-center rounded-full bg-alert-50 text-alert-600 mx-auto"
        >
          <svg lucideShieldAlert [size]="26" [strokeWidth]="1.75"></svg>
        </span>

        <h2 class="mt-5 text-base font-semibold text-moza-800">Não tem acesso a esta área</h2>
        <p class="mt-2 text-sm leading-relaxed text-moza-500">
          A sua conta está autenticada, mas esta página é de uma área a que não pertence.
        </p>

        <p
          class="mt-5 inline-flex items-center gap-1.5 rounded-full bg-moza-50 px-3 py-1 text-xs font-medium text-moza-600"
        >
          As suas áreas: {{ areas() }}
        </p>

        <div class="mt-6 flex items-center justify-center gap-2 border-t border-gray-100 pt-5">
          <svg lucideLifeBuoy [size]="15" [strokeWidth]="1.9" class="shrink-0 text-moza-400"></svg>
          <p class="text-xs text-moza-400">
            Para suporte, contacte
            <a href="mailto:dalton.chivambo@mozabanco.co.mz" class="font-medium text-moza-600 hover:underline"
              >dalton.chivambo&#64;mozabanco.co.mz</a
            >
          </p>
        </div>
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
}
