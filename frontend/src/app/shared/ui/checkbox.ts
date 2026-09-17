import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { LucideCheck, LucideMinus } from '@lucide/angular';

/**
 * A caixa de selecção da aplicação: a caixa desenhada, e a `input` verdadeira
 * lá dentro, escondida mas acessível — teclado e leitores de ecrã vêem uma
 * checkbox normal.
 *
 * Vai dentro de um `<label>` de quem usa, para o texto ao lado também marcar:
 *
 *   <label class="flex items-center gap-2.5">
 *     <app-checkbox [checked]="x" (toggled)="…" />
 *     Texto
 *   </label>
 *
 * `indeterminate` é o traço da caixa-mestra quando só parte está marcada; ganha
 * a `checked`, como no HTML.
 */
@Component({
  selector: 'app-checkbox',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [LucideCheck, LucideMinus],
  host: { class: 'inline-flex shrink-0' },
  template: `
    <span
      aria-hidden="true"
      class="inline-flex size-4 items-center justify-center rounded border transition-colors"
      [class]="
        checked() || indeterminate()
          ? 'border-moza-700 bg-moza-700 text-white'
          : 'border-gray-300 bg-white'
      "
      [class.opacity-50]="disabled()"
    >
      @if (indeterminate()) {
        <svg lucideMinus [size]="11" [strokeWidth]="3.5"></svg>
      } @else if (checked()) {
        <svg lucideCheck [size]="11" [strokeWidth]="3.5"></svg>
      }
    </span>
    <input
      type="checkbox"
      class="sr-only"
      [checked]="checked()"
      [indeterminate]="indeterminate()"
      [disabled]="disabled()"
      [attr.aria-label]="ariaLabel()"
      (change)="toggled.emit()"
    />
  `,
})
export class CheckboxComponent {
  readonly checked = input(false);
  readonly indeterminate = input(false);
  readonly disabled = input(false);
  /** Só quando não há `<label>` com texto à volta. */
  readonly ariaLabel = input<string | null>(null);

  /** Pediu-se para trocar — quem usa decide o novo estado. */
  readonly toggled = output<void>();
}
