import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  input,
  output,
  signal,
} from '@angular/core';
import { LucideCircleCheck, LucideTriangleAlert, LucideX } from '@lucide/angular';

export type ToastVariant = 'success' | 'error';

/** Um número do aviso — «Fechos processados · 29 317». `warning` chama a atenção para ele. */
export interface ToastFact {
  readonly label: string;
  readonly value: string;
  readonly tone?: 'neutral' | 'warning';
}

/**
 * O que um aviso diz: o título é o que aconteceu, em poucas palavras; o texto,
 * se houver, uma frase com o que o operador precisa de saber; os números, o
 * resultado em si — cada um na sua linha, em vez de enfiados numa frase.
 */
export interface Toast {
  readonly title: string;
  readonly detail?: string | null;
  readonly facts?: readonly ToastFact[];
}

const AUTO_DISMISS_MS: Record<ToastVariant, number> = { success: 10_000, error: 16_000 };

const VARIANTS: Record<ToastVariant, { ring: string; chip: string; accent: string }> = {
  success: {
    ring: 'ring-emerald-200/70',
    chip: 'bg-emerald-50 text-emerald-600',
    accent: 'bg-emerald-500',
  },
  error: {
    ring: 'ring-alert-200/70',
    chip: 'bg-alert-50 text-alert-600',
    accent: 'bg-alert-500',
  },
};

/**
 * Aviso flutuante, ao centro do topo do ecrã — fecha-se sozinho ou no ✕, pausa ao
 * passar o rato. O erro fica mais tempo (16s vs 10s): costuma trazer decisão a tomar.
 */
@Component({
  selector: 'app-toast',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [LucideCircleCheck, LucideTriangleAlert, LucideX],
  template: `
    <div class="pointer-events-none fixed inset-x-0 top-4 z-50 flex justify-center px-4 sm:top-6">
      <div
        [attr.role]="variant() === 'error' ? 'alert' : 'status'"
        aria-live="polite"
        (mouseenter)="paused.set(true)"
        (mouseleave)="paused.set(false)"
        class="pointer-events-auto relative flex w-full max-w-md items-start gap-3 overflow-hidden rounded-2xl bg-white py-4 pr-3 pl-4 text-sm shadow-xl ring-1 motion-safe:animate-[toast-in_220ms_cubic-bezier(0.16,1,0.3,1)]"
        [class]="style().ring"
      >
        <span
          class="flex size-9 shrink-0 items-center justify-center rounded-full"
          [class]="style().chip"
        >
          @if (variant() === 'success') {
            <svg lucideCircleCheck [size]="19" [strokeWidth]="1.9"></svg>
          } @else {
            <svg lucideTriangleAlert [size]="19" [strokeWidth]="1.9"></svg>
          }
        </span>

        <div class="min-w-0 flex-1 pt-0.5">
          <p class="leading-snug font-semibold text-gray-900">{{ toast().title }}</p>
          @if (toast().detail; as detail) {
            <p class="mt-0.5 leading-snug text-gray-500">{{ detail }}</p>
          }

          @if (toast().facts?.length) {
            <dl
              class="mt-2.5 divide-y divide-gray-100 rounded-xl bg-gray-50/80 px-3 ring-1 ring-gray-100"
            >
              @for (fact of toast().facts; track fact.label) {
                <div class="flex items-baseline justify-between gap-4 py-1.5 text-xs">
                  <dt class="flex min-w-0 items-center gap-1.5 text-gray-500">
                    @if (fact.tone === 'warning') {
                      <span class="size-1.5 shrink-0 rounded-full bg-amber-500"></span>
                    }
                    {{ fact.label }}
                  </dt>
                  <dd
                    class="font-semibold whitespace-nowrap tabular-nums"
                    [class]="fact.tone === 'warning' ? 'text-amber-700' : 'text-gray-900'"
                  >
                    {{ fact.value }}
                  </dd>
                </div>
              }
            </dl>
          }
        </div>

        <button
          type="button"
          (click)="dismiss.emit()"
          aria-label="Fechar aviso"
          class="shrink-0 rounded-full p-1.5 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-900"
        >
          <svg lucideX [size]="15" [strokeWidth]="2"></svg>
        </button>

        <!-- @for sobre um valor só, de propósito: o track troca o elemento e reinicia a animação CSS. -->
        @for (phase of [paused() ? 'paused' : 'running']; track phase) {
          <span
            aria-hidden="true"
            class="absolute inset-x-0 bottom-0 h-1 origin-left motion-safe:animate-[toast-progress_linear_forwards]"
            [class]="style().accent"
            [style.animationDuration.ms]="duration()"
            [style.animationPlayState]="phase"
          ></span>
        }
      </div>
    </div>
  `,
})
export class ToastComponent {
  /** Um texto só também serve — fica como título. */
  readonly message = input.required<Toast | string>();
  readonly variant = input<ToastVariant>('success');
  readonly dismiss = output<void>();

  protected readonly paused = signal(false);
  protected readonly duration = computed(() => AUTO_DISMISS_MS[this.variant()]);
  protected readonly style = computed(() => VARIANTS[this.variant()]);
  protected readonly toast = computed<Toast>(() => {
    const message = this.message();
    return typeof message === 'string' ? { title: message } : message;
  });

  constructor() {
    effect((onCleanup) => {
      if (this.paused()) return;

      // Ler `message()` aqui é o que reinicia o temporizador em avisos seguidos:
      // uma mensagem nova é um aviso novo, e merece o tempo todo outra vez.
      this.message();
      const timer = setTimeout(() => this.dismiss.emit(), this.duration());
      onCleanup(() => clearTimeout(timer));
    });
  }
}
