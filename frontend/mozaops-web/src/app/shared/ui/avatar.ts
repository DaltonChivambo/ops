import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

/**
 * Iniciais em círculo, com cor derivada do nome.
 *
 * Porte de `client/src/shared/ui/Avatar.tsx`. A cor sai de um hash do nome e
 * não de um aleatório: a mesma pessoa tem sempre a mesma cor, em qualquer
 * sessão e em qualquer ecrã. É o que a torna reconhecível de relance numa lista.
 *
 * `aria-hidden`: as iniciais são decoração. Quem lê por leitor de ecrã já tem o
 * nome por extenso ao lado — anunciar «AS» a seguir a «Ana Sousa» é ruído.
 */
@Component({
  selector: 'app-avatar',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <span
      class="inline-flex shrink-0 items-center justify-center rounded-full font-semibold text-white select-none"
      [style.width.px]="size()"
      [style.height.px]="size()"
      [style.fontSize.px]="size() * 0.38"
      [style.backgroundColor]="background()"
      aria-hidden="true"
    >
      {{ initials() }}
    </span>
  `,
})
export class AvatarComponent {
  readonly name = input.required<string>();
  readonly size = input(36);
  /** Sobrepõe a cor derivada — para quando o contexto já dita uma. */
  readonly color = input<string | undefined>(undefined);

  readonly initials = computed(() => initialsOf(this.name()));
  readonly background = computed(() => this.color() ?? colorOf(this.name()));
}

const PALETTE = ['#6d28d9', '#0891b2', '#059669', '#d97706', '#dc2626', '#4f46e5'];

function initialsOf(name: string): string {
  const parts = name.trim().split(/\s+/);
  const first = parts.at(0)?.[0] ?? '';
  const last = parts.length > 1 ? (parts.at(-1)?.[0] ?? '') : '';
  return (first + last).toUpperCase();
}

function colorOf(name: string): string {
  let hash = 0;
  for (const char of name) hash = (hash * 31 + char.codePointAt(0)!) | 0;
  return PALETTE[Math.abs(hash) % PALETTE.length];
}
