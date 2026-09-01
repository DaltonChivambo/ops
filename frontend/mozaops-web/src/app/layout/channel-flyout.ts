import { ChangeDetectionStrategy, Component, computed, inject, input, output } from '@angular/core';
import { Router } from '@angular/router';
import {
  LucideArrowLeft,
  LucideFileCheck2,
  LucideLandmark,
  LucideLayoutGrid,
  LucideSmartphoneNfc,
  LucideStore,
  LucideX,
} from '@lucide/angular';

import { type Feature, type NavModule } from '../core/navigation';

/** O painel de funcionalidades de um canal, ao lado da barra — fecha ao clicar fora, no ✕, ou com Escape. */
@Component({
  selector: 'app-channel-flyout',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    LucideArrowLeft,
    LucideFileCheck2,
    LucideLandmark,
    LucideLayoutGrid,
    LucideSmartphoneNfc,
    LucideStore,
    LucideX,
  ],
  host: {
    '(document:keydown.escape)': 'closed.emit()',
  },
  template: `
    @let mod = module();

    <!-- Overlay transparente: fecha ao clicar fora, sem escurecer o conteúdo. -->
    <div class="fixed inset-0 z-40" aria-hidden="true" (click)="closed.emit()"></div>

    <div
      role="menu"
      [attr.aria-label]="'Funcionalidades de ' + mod.label"
      class="fixed inset-y-0 z-50 flex w-72 flex-col overflow-y-auto border-r border-gray-100 bg-white px-5 py-5 shadow-xl sm:w-80"
      [class]="collapsed() ? 'left-0 lg:left-[4.75rem]' : 'left-0 lg:left-[16.5rem]'"
    >
      <div class="mb-5 flex items-center gap-3 border-b border-gray-100 pb-5">
        <button
          type="button"
          class="inline-flex size-8 shrink-0 items-center justify-center rounded-full text-gray-600 hover:bg-moza-50 lg:hidden"
          aria-label="Voltar ao menu"
          (click)="closed.emit()"
        >
          <svg lucideArrowLeft [size]="18" [strokeWidth]="1.8"></svg>
        </button>

        <span
          class="inline-flex size-10 shrink-0 items-center justify-center rounded-xl bg-moza-100 text-moza-700"
        >
          @switch (mod.icon) {
            @case ('smartphone-nfc') {
              <svg lucideSmartphoneNfc [size]="20" [strokeWidth]="1.8"></svg>
            }
            @case ('landmark') {
              <svg lucideLandmark [size]="20" [strokeWidth]="1.8"></svg>
            }
            @case ('store') {
              <svg lucideStore [size]="20" [strokeWidth]="1.8"></svg>
            }
            @default {
              <svg lucideLayoutGrid [size]="20" [strokeWidth]="1.8"></svg>
            }
          }
        </span>

        <div class="min-w-0 flex-1">
          <p class="truncate text-base font-bold text-gray-900">{{ mod.label }}</p>
          <!-- «0 funcionalidades» é uma contagem a fingir que informa; para um
               canal sem nada construído, diz-se isso mesmo. -->
          <p class="truncate text-xs text-gray-400">
            @if (mod.features.length === 0) {
              Sem automações
            } @else {
              {{ mod.features.length }} funcionalidade{{ mod.features.length === 1 ? '' : 's' }}
            }
          </p>
        </div>

        <button
          type="button"
          class="hidden size-8 shrink-0 items-center justify-center rounded-full text-gray-400 transition-colors hover:bg-moza-50 hover:text-gray-600 lg:inline-flex"
          aria-label="Fechar"
          (click)="closed.emit()"
        >
          <svg lucideX [size]="18" [strokeWidth]="1.8"></svg>
        </button>
      </div>

      <button
        type="button"
        role="menuitem"
        (click)="openModule()"
        class="flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-left text-sm font-semibold text-gray-700 transition-colors hover:bg-moza-50 hover:text-gray-900"
      >
        <svg lucideLayoutGrid [size]="18" [strokeWidth]="1.8" class="shrink-0 text-moza-700"></svg>
        Visão Geral
      </button>

      <div class="my-4 border-t border-gray-100" aria-hidden="true"></div>

      @for (group of grouped(); track group.category; let groupIndex = $index) {
        <div [class]="groupIndex > 0 ? 'mt-5 border-t border-gray-100 pt-5' : ''">
          <p class="mb-2 px-3 text-2xs font-semibold tracking-wider text-gray-400 uppercase">
            {{ group.category }}
          </p>
          <ul class="flex flex-col gap-1">
            @for (feature of group.features; track feature.id) {
              <li>
                <button
                  type="button"
                  role="menuitem"
                  (click)="openFeature(feature)"
                  class="relative flex w-full items-start gap-2.5 rounded-xl px-3 py-2.5 text-left text-sm text-gray-600 transition-colors hover:bg-moza-50 hover:text-gray-900"
                >
                  <svg
                    lucideFileCheck2
                    [size]="18"
                    [strokeWidth]="1.8"
                    class="mt-0.5 shrink-0"
                  ></svg>
                  {{ feature.title }}
                </button>
              </li>
            }
          </ul>
        </div>
      } @empty {
        <p class="px-3 py-1 text-sm text-gray-400">
          Ainda não há automações construídas para este canal.
        </p>
      }
    </div>
  `,
})
export class ChannelFlyoutComponent {
  private readonly router = inject(Router);

  readonly module = input.required<NavModule>();
  readonly collapsed = input(false);

  readonly closed = output<void>();
  readonly selected = output<void>();

  /** Agrupa por categoria preservando a ordem de declaração. */
  protected readonly grouped = computed(() => {
    const groups = new Map<string, Feature[]>();
    for (const feature of this.module().features) {
      const group = groups.get(feature.category);
      if (group) group.push(feature);
      else groups.set(feature.category, [feature]);
    }
    return [...groups.entries()].map(([category, features]) => ({ category, features }));
  });

  protected openModule(): void {
    void this.router.navigate(['/', this.module().id]);
    this.selected.emit();
  }

  protected openFeature(feature: Feature): void {
    void this.router.navigate(['/', this.module().id, feature.id]);
    this.selected.emit();
  }
}
