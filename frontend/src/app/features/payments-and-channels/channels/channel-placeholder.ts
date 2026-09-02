import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import { LucideConstruction, LucideSearchX } from '@lucide/angular';

import { findModule } from '../../../core/navigation';
import { CardComponent } from '../../../shared/ui/card';

/** O que sobra de um canal sem automação pronta — ver a openSingleFeature. */
@Component({
  selector: 'app-channel-placeholder',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CardComponent, LucideConstruction, LucideSearchX],
  template: `
    @let mod = module();

    <section appCard class="flex flex-col items-center gap-3 py-16 text-center">
      <span
        class="inline-flex size-12 items-center justify-center rounded-xl bg-moza-100 text-moza-700"
      >
        @if (mod) {
          <svg lucideConstruction [size]="24" [strokeWidth]="1.8"></svg>
        } @else {
          <svg lucideSearchX [size]="24" [strokeWidth]="1.8"></svg>
        }
      </span>

      @if (mod) {
        <p class="font-semibold text-gray-900">Ainda não disponível</p>
        <p class="max-w-sm text-sm text-gray-500">
          Não há nada para mostrar em {{ mod.label }} por agora. Esta secção aparece aqui assim que
          for construída.
        </p>
      } @else {
        <p class="font-semibold text-gray-900">Este endereço não existe</p>
        <p class="max-w-sm text-sm text-gray-500">
          Verifique o endereço, ou escolha uma secção na navegação à esquerda.
        </p>
      }
    </section>
  `,
})
export class ChannelPlaceholderComponent {
  /** Chega por `withComponentInputBinding()`, directamente do parâmetro de rota. */
  readonly moduleId = input.required<string>();
  protected readonly module = computed(() => findModule(this.moduleId()));
}
