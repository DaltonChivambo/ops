import { ChangeDetectionStrategy, Component, computed, inject, input } from '@angular/core';
import { RouterLink } from '@angular/router';

import { SessionStore } from '../../../core/auth/session.store';
import { findModule } from '../../../core/navigation';
import { HeaderComponent } from '../../../layout/header';

/**
 * Catálogo de funcionalidades de um canal.
 *
 * O `moduleId` chega por `withComponentInputBinding()`, directamente do
 * parâmetro de rota — sem `ActivatedRoute` nem subscrição.
 */
@Component({
  selector: 'app-channel-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [HeaderComponent, RouterLink],
  template: `
    @let mod = module();

    <app-header [title]="mod?.label ?? 'Módulo'" [subtitle]="subtitle()" />

    <div class="p-6">
      @if (!mod) {
        <div class="rounded-lg border border-moza-200 bg-white p-8 text-center">
          <p class="font-medium text-moza-800">Este módulo não existe.</p>
          <p class="mt-1 text-sm text-moza-500">Verifique o endereço.</p>
        </div>
      } @else if (mod.features.length === 0) {
        <div class="rounded-lg border border-moza-200 bg-white p-8 text-center">
          <p class="font-medium text-moza-800">Este módulo ainda não foi construído.</p>
        </div>
      } @else {
        <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          @for (feature of mod.features; track feature.id) {
            <article
              class="flex flex-col rounded-lg border border-moza-200 bg-white p-5 transition"
              [class.opacity-60]="!feature.available"
            >
              <div class="flex items-start justify-between gap-3">
                <span
                  class="rounded-full bg-moza-100 px-2.5 py-0.5 text-xs font-medium text-moza-600"
                >
                  {{ feature.category }}
                </span>
                @if (!feature.available) {
                  <span class="text-xs font-medium text-moza-400">Em desenvolvimento</span>
                }
              </div>

              <h2 class="mt-3 font-semibold text-moza-800">{{ feature.title }}</h2>
              <p class="mt-2 grow text-sm leading-relaxed text-moza-500">
                {{ feature.description }}
              </p>

              @if (feature.available) {
                <a
                  [routerLink]="['/', moduleId(), feature.id]"
                  class="mt-4 self-start rounded-md bg-moza-700 px-3.5 py-2 text-sm font-medium text-white transition hover:bg-moza-800"
                >
                  {{ session.canExecute() ? 'Abrir' : 'Consultar' }}
                </a>
              } @else {
                <button
                  type="button"
                  disabled
                  class="mt-4 self-start cursor-not-allowed rounded-md bg-moza-700 px-3.5 py-2 text-sm font-medium text-white opacity-50"
                >
                  {{ session.canExecute() ? 'Abrir' : 'Consultar' }}
                </button>
              }
            </article>
          }
        </div>
      }
    </div>
  `,
})
export class ChannelPageComponent {
  readonly session = inject(SessionStore);

  readonly moduleId = input.required<string>();
  readonly module = computed(() => findModule(this.moduleId()));

  readonly subtitle = computed(() => {
    const count = this.module()?.features.length ?? 0;
    if (count === 0) return '';
    return `${count} ${count === 1 ? 'funcionalidade disponível' : 'funcionalidades disponíveis'}`;
  });
}
