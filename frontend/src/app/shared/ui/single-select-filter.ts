import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  computed,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { LucideCheck, LucideChevronDown } from '@lucide/angular';

import { numberFormatter } from '../format';

/** Uma escolha do filtro: o que se mostra, e quantas linhas dá. */
export interface SingleFilterOption {
  readonly id: string;
  /** O que se lê no painel, por extenso. */
  readonly label: string;
  /** O que se lê no botão, onde o rótulo do filtro já dá o contexto. Sem isto,
   *  vai o `label` — e o botão fica a repetir o que está à sua esquerda. */
  readonly short?: string;
  /** Classe da marca de cor, quando a escolha tem uma. Vazio esconde a marca. */
  readonly dot?: string;
  readonly count: number;
}

/**
 * O filtro de escolha ÚNICA das listas — irmão do `app-multi-select-filter`,
 * com o mesmo botão e o mesmo painel, mas com marca de escolhido em vez de
 * caixas, porque as opções não se combinam.
 *
 * Existe porque um interruptor de ligar e desligar não serve para filtrar: o
 * botão muda de cor, mas quem chega ao ecrã não sabe se está ligado nem o que
 * a lista está a esconder. Aqui a escolha lê-se no próprio botão, antes de lhe
 * tocar, e as alternativas estão escritas em vez de subentendidas.
 *
 * A primeira opção é a neutra («todos»): é ela que deixa o botão em cinzento,
 * e qualquer outra pinta-o, para se ver de relance que a lista está reduzida.
 *
 * O ícone entra por projecção — `<svg lucideCopy filterIcon …>` —, como no outro.
 */
@Component({
  selector: 'app-single-select-filter',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [LucideCheck, LucideChevronDown],
  host: {
    class: 'relative shrink-0',
    '(document:mousedown)': 'onDocumentMouseDown($event)',
    '(document:keydown.escape)': 'open.set(false)',
  },
  template: `
    <button
      type="button"
      (click)="open.set(!open())"
      aria-haspopup="listbox"
      [attr.aria-expanded]="open()"
      class="inline-flex items-center gap-2 rounded-xl border px-3.5 py-2.5 text-sm font-semibold transition-colors"
      [class]="
        neutral()
          ? 'border-gray-100 bg-gray-50 text-gray-600 hover:text-gray-900'
          : 'border-moza-200 bg-moza-50 text-moza-700'
      "
    >
      <ng-content select="[filterIcon]" />
      <span class="font-medium opacity-60">{{ label() }}:</span>
      {{ currentLabel() }}
      <svg
        lucideChevronDown
        [size]="14"
        [strokeWidth]="2.4"
        class="shrink-0 text-gray-400 transition-transform"
        [class.rotate-180]="open()"
      ></svg>
    </button>

    @if (open()) {
      <div
        role="listbox"
        class="absolute top-full right-0 z-30 mt-1.5 w-64 rounded-xl border border-gray-100 bg-white p-1 shadow-lg"
      >
        @for (option of options(); track option.id) {
          <button
            type="button"
            role="option"
            [attr.aria-selected]="option.id === selected()"
            (click)="choose(option.id)"
            class="flex w-full cursor-pointer items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm transition-colors hover:bg-gray-50"
            [class]="option.id === selected() ? 'font-semibold text-gray-900' : 'text-gray-600'"
          >
            <span class="flex size-4 shrink-0 items-center justify-center">
              @if (option.id === selected()) {
                <svg lucideCheck [size]="14" [strokeWidth]="2.6" class="text-moza-600"></svg>
              }
            </span>
            @if (option.dot) {
              <span class="size-2 shrink-0 rounded-full" [class]="option.dot"></span>
            }
            <span class="flex-1 font-medium">{{ option.label }}</span>
            <span class="text-xs text-gray-400 tabular-nums">{{ n(option.count) }}</span>
          </button>
        }
      </div>
    }
  `,
})
export class SingleSelectFilterComponent {
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);

  /** O verbo do filtro, curto — sai no botão como «Mostrar: Todos». */
  readonly label = input.required<string>();
  readonly options = input.required<readonly SingleFilterOption[]>();
  readonly selected = input.required<string>();
  readonly changed = output<string>();

  protected readonly open = signal(false);

  protected readonly current = computed(() =>
    this.options().find((option) => option.id === this.selected()),
  );

  protected readonly currentLabel = computed(() => {
    const current = this.current();
    return current ? (current.short ?? current.label) : '';
  });

  /** A primeira opção é a que não filtra nada — daí o botão ficar neutro nela. */
  protected readonly neutral = computed(() => this.selected() === this.options()[0]?.id);

  protected choose(id: string): void {
    this.open.set(false);
    if (id !== this.selected()) this.changed.emit(id);
  }

  protected onDocumentMouseDown(event: MouseEvent): void {
    if (!this.host.nativeElement.contains(event.target as Node)) this.open.set(false);
  }

  protected n = (value: number) => numberFormatter.format(value);
}
