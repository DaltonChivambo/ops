import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  computed,
  effect,
  inject,
  input,
  linkedSignal,
  output,
  signal,
} from '@angular/core';
import {
  LucideCheck,
  LucideChevronDown,
  LucideLink2,
  LucideLoaderCircle,
  LucidePlus,
  LucideTicket,
  LucideX,
} from '@lucide/angular';

import {
  daysBetween,
  formatAmount,
  formatDate,
  formatDateValue,
  formatDayCount,
  formatSignedAmount,
  numberFormatter,
  parseIsoDate,
  toIsoDate,
} from '../../../../../../shared/format';
import {
  CASE_STATUSES,
  CASE_STATUS_DOT,
  CASE_STATUS_LABEL,
  CASE_STATUS_WAIT,
} from '../data/case-status';
import { MAX_E_TICKET_LENGTH, eTicketProblem } from '../data/e-ticket';
import {
  creditedWhen,
  withinPeriod,
  sameAmount,
  sameDraft,
  toDraft,
  toMatches,
  type MatchDraft,
} from '../data/matching';
import { ReconciliationApi } from '../data/reconciliation-api.service';
import {
  SOURCE_LABEL,
  slaDotOf,
  slaOf,
  slaPhrase,
  slaToneOf,
  startOfToday,
  type SlaView,
} from '../data/sla';
import { STATE_CHIP, STATE_DOT, STATE_LABEL } from '../data/state-options';
import type {
  CaseMatches,
  CasePatch,
  CaseStatus,
  ClosingDetail,
  CreditMovement,
  KeyBreakdown,
  PendingCase,
  SlaSettings,
} from '../data/models';

/**
 * Painel lateral com os dois lados de uma chave — fechos SIMO e movimentos Banka.
 * A unidade é a CHAVE e não o fecho: o crédito do Banka é da chave, um fecho
 * isolado não tem crédito próprio.
 */
@Component({
  selector: 'app-key-detail-panel',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    LucideCheck,
    LucideChevronDown,
    LucideLink2,
    LucideLoaderCircle,
    LucidePlus,
    LucideTicket,
    LucideX,
  ],
  host: {
    '(document:keydown.escape)': 'closed.emit()',
  },
  template: `
    @let d = detail();

    <div class="fixed inset-0 z-40 bg-gray-900/20" aria-hidden="true" (click)="closed.emit()"></div>

    <aside
      role="dialog"
      aria-modal="true"
      [attr.aria-label]="'Fecho do POS ' + d.posId + ', período ' + d.period"
      class="fixed inset-y-0 right-0 z-50 flex w-full max-w-2xl flex-col bg-white shadow-2xl"
    >
      <header class="flex items-start gap-3 border-b border-gray-100 px-5 py-4">
        <div class="min-w-0 flex-1">
          <div class="flex flex-wrap items-center gap-2">
            <h2 class="text-lg font-bold text-gray-900 tabular-nums">POS {{ d.posId }}</h2>
            <span
              class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-bold whitespace-nowrap"
              [class]="chip()"
            >
              <span class="size-1.5 rounded-full" [class]="dot()"></span>
              {{ stateLabel() }}
            </span>
          </div>

          <p class="mt-0.5 truncate text-sm text-gray-500">{{ d.merchant }}</p>

          <div class="mt-2 flex flex-wrap items-baseline gap-x-4 gap-y-1 text-xs">
            <span [class]="meta">
              <span class="text-gray-400">Conta</span>
              <span [class]="metaValue">{{ d.accountNumber }}</span>
            </span>
            <span [class]="meta">
              <span class="text-gray-400">Período</span>
              <span [class]="metaValue">{{ d.period }}</span>
            </span>
            <span [class]="meta">
              <span class="text-gray-400">Fecho</span>
              <span [class]="metaValue">{{ closingType() }}</span>
            </span>
            <span [class]="meta">
              <span class="text-gray-400">Chave</span>
              <span [class]="metaValue">{{ d.key }}</span>
            </span>
          </div>
        </div>

        <button
          type="button"
          (click)="closed.emit()"
          aria-label="Fechar"
          class="inline-flex size-8 shrink-0 items-center justify-center rounded-lg text-gray-400 transition-colors hover:bg-gray-50 hover:text-gray-900"
        >
          <svg lucideX [size]="18" [strokeWidth]="2.2"></svg>
        </button>
      </header>

      <div class="min-h-0 flex-1 overflow-y-auto px-5 py-5">
        @if (error(); as message) {
          <p class="rounded-xl bg-alert-50 px-4 py-3 text-sm text-alert-700">{{ message }}</p>
        }

        @if (!data() && !error()) {
          <p class="mt-8 flex items-center justify-center gap-2 text-sm text-gray-400">
            <svg lucideLoaderCircle [size]="15" [strokeWidth]="2" class="animate-spin"></svg>
            A abrir o fecho…
          </p>
        }

        @if (data(); as breakdown) {
          <!-- Apuramento à cabeça, é a conclusão; as listas por baixo são a demonstração.
               Empilha abaixo do sm: o painel ocupa a largura toda num ecrã
               estreito, e três montantes lado a lado ficam ilegíveis. -->
          <section
            class="grid grid-cols-1 gap-4 rounded-xl border border-gray-100 px-4 py-3.5 sm:grid-cols-3"
          >
            <div class="min-w-0">
              <p [class]="totalLabel">Apurado na SIMO</p>
              <p [class]="totalValue + ' text-gray-900'">
                {{ amount(simoTotal()) }}<span [class]="mzn">MZN</span>
              </p>
            </div>
            <div class="min-w-0">
              <p [class]="totalLabel">Creditado no Banka</p>
              <p [class]="totalValue + ' text-gray-900'">
                {{ amount(bankaTotal()) }}<span [class]="mzn">MZN</span>
              </p>
            </div>
            <div class="min-w-0">
              <p [class]="totalLabel">Diferença</p>
              <p
                [class]="totalValue"
                [class.text-emerald-600]="difference() === 0"
                [class.text-alert-600]="difference() !== 0"
              >
                {{ signed(difference()) }}<span [class]="mzn">MZN</span>
              </p>
            </div>
          </section>

          @if (breakdown.case; as pendingCase) {
            @let sla = slaOf(pendingCase);
            <!-- Logo a seguir ao apuramento, antes das listas: é o que se vem cá
                 fazer quando se abre um caso, e no fim do painel obrigava a descer. -->
            <section class="mt-4 rounded-xl border border-gray-100 px-4 py-3.5">
              <!-- O estado do prazo à cabeça, como na tabela: é a leitura que se
                   vem cá fazer. O detalhe da conta fica na grelha por baixo. -->
              <div class="flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
                <h3 [class]="sectionTitle">Caso para análise</h3>
                <span class="flex items-center gap-1.5 whitespace-nowrap">
                  <span class="size-1.5 shrink-0 rounded-full" [class]="slaDotTone(sla)"></span>
                  <span class="text-xs font-semibold" [class]="slaTone(sla)">
                    {{ slaPhrase(sla) }}
                  </span>
                </span>
              </div>

              <!-- É aqui, e só aqui, que o caso se trata: um formulário com os
                   dois campos e um «Guardar» explícito. Nada grava ao escolher
                   uma opção ou ao sair de um campo — muda-se, revê-se, guarda-se. -->
              <form
                class="mt-3 rounded-xl bg-gray-50/80 p-3.5 ring-1 ring-gray-100"
                (submit)="$event.preventDefault(); save(pendingCase)"
              >
                <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <label class="block min-w-0">
                    <span [class]="fieldLabel">Fase do tratamento</span>
                    <span class="relative mt-1 block">
                      <span
                        class="pointer-events-none absolute top-1/2 left-3 size-2 -translate-y-1/2 rounded-full"
                        [class]="statusDot[draftStatus()]"
                      ></span>
                      <select
                        [value]="draftStatus()"
                        (change)="draftStatus.set($any($event.target).value)"
                        class="w-full cursor-pointer appearance-none rounded-lg border border-gray-200 bg-white py-2 pr-9 pl-7 text-sm font-semibold text-gray-900 outline-none transition-colors hover:border-gray-300 focus:border-moza-400 focus:ring-2 focus:ring-moza-100"
                      >
                        @for (status of statuses; track status) {
                          <option [value]="status">{{ statusLabel[status] }}</option>
                        }
                      </select>
                      <svg
                        lucideChevronDown
                        [size]="15"
                        [strokeWidth]="2.2"
                        class="pointer-events-none absolute top-1/2 right-3 -translate-y-1/2 text-gray-400"
                      ></svg>
                    </span>
                    <!-- O tempo é do estado GUARDADO: um rascunho ainda não mudou nada. -->
                    <span class="mt-1 block text-2xs text-gray-400">
                      @if (pendingCase.status === 'resolved' && pendingCase.resolvedAt) {
                        Regularizado em {{ date(pendingCase.resolvedAt) }}
                      } @else {
                        {{ capitalize(statusWait[pendingCase.status]) }}
                        {{ dayCount(daysInStatus(pendingCase)) }}
                      }
                    </span>
                  </label>

                  <label class="block min-w-0">
                    <span [class]="fieldLabel">e-Ticket</span>
                    <span class="relative mt-1 block">
                      <svg
                        lucideTicket
                        [size]="15"
                        [strokeWidth]="2"
                        class="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-gray-400"
                      ></svg>
                      <!-- O maxlength é conforto, não protecção: quem recusa o que
                           não tem forma de referência é o servidor (domain/e_ticket.py). -->
                      <input
                        type="text"
                        autocomplete="off"
                        spellcheck="false"
                        [attr.maxlength]="maxETicket"
                        placeholder="Ex.: INC-4210"
                        [value]="draftETicket()"
                        (input)="draftETicket.set($any($event.target).value)"
                        [attr.aria-invalid]="eTicketError() ? 'true' : null"
                        aria-describedby="e-ticket-hint"
                        class="w-full rounded-lg border bg-white py-2 pr-3 pl-9 font-mono text-sm font-semibold text-gray-900 outline-none transition-colors placeholder:font-sans placeholder:font-normal placeholder:text-gray-400 focus:ring-2"
                        [class]="
                          eTicketError()
                            ? 'border-alert-300 focus:border-alert-500 focus:ring-alert-100'
                            : 'border-gray-200 hover:border-gray-300 focus:border-moza-400 focus:ring-moza-100'
                        "
                      />
                    </span>
                    <span
                      id="e-ticket-hint"
                      class="mt-1 block text-2xs"
                      [class]="eTicketError() ? 'text-alert-600' : 'text-gray-400'"
                    >
                      {{ eTicketError() ?? 'A referência do pedido aberto na SIMO.' }}
                    </span>
                  </label>
                </div>

                <div
                  class="mt-3.5 flex flex-wrap items-center justify-end gap-2 border-t border-gray-200/70 pt-3"
                >
                  @if (dirty()) {
                    <span class="mr-auto text-xs font-medium text-amber-700">
                      Alterações por guardar
                    </span>
                    <button
                      type="button"
                      (click)="discard(pendingCase)"
                      class="rounded-lg px-3 py-2 text-sm font-semibold text-gray-600 transition-colors hover:bg-gray-100 hover:text-gray-900"
                    >
                      Cancelar
                    </button>
                  }
                  <button
                    type="submit"
                    [disabled]="!dirty() || eTicketError() !== null"
                    class="inline-flex items-center gap-1.5 rounded-lg bg-moza-700 px-3.5 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-moza-800 disabled:cursor-not-allowed disabled:bg-gray-200 disabled:text-gray-400 disabled:shadow-none"
                  >
                    <svg lucideCheck [size]="15" [strokeWidth]="2.6"></svg>
                    Guardar
                  </button>
                </div>
              </form>

              <dl class="mt-3.5 grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-3">
                <!-- Donde conta, até quando, e há quanto tempo. A origem vai
                     junto da data: é ela que diz qual dos dois lados manda. -->
                <div class="min-w-0">
                  <dt [class]="fieldLabel">Conta desde</dt>
                  <dd [class]="fieldValue">
                    {{ date(pendingCase.firstDate) }}
                    <span class="text-2xs font-medium text-gray-400">
                      · {{ sourceLabel[pendingCase.firstDateSource] }}
                    </span>
                  </dd>
                </div>
                <div class="min-w-0">
                  <dt [class]="fieldLabel">Data limite</dt>
                  <dd [class]="fieldValue">{{ dateValue(sla.deadline) }}</dd>
                </div>
                <div class="min-w-0">
                  <dt [class]="fieldLabel">
                    {{ pendingCase.status === 'resolved' ? 'Levou' : 'Em aberto há' }}
                  </dt>
                  <dd [class]="fieldValue">{{ dayCount(sla.age) }}</dd>
                </div>
              </dl>
            </section>
          }

          @if (canMatch() && breakdown.case; as pendingCase) {
            <!-- Períodos duplicados: a soma não diz que crédito pagou que fecho. Em
                 vez das duas listas soltas, um quadro só — cada fecho da SIMO na
                 linha do crédito do Banka que o paga, e cada lado aparece uma vez.
                 Os pares pelo valor chegam já propostos: o caso comum é confirmar. -->
            <section class="mt-4 rounded-xl border border-gray-100 px-4 py-3.5">
              <div class="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
                <div class="min-w-0">
                  <h3 [class]="sectionTitle">Conciliação</h3>
                  <p class="mt-0.5 text-xs text-gray-500">
                    Cada fecho da SIMO ligado ao crédito do Banka de valor igual.
                  </p>
                </div>
                <div class="flex items-center gap-2.5">
                  <span
                    class="block h-1.5 w-20 overflow-hidden rounded-full bg-gray-100"
                    aria-hidden="true"
                  >
                    <span
                      class="block h-full rounded-full transition-[width] duration-300"
                      [class]="allSaved() ? 'bg-emerald-500' : 'bg-moza-500'"
                      [style.width.%]="progress()"
                    ></span>
                  </span>
                  <span
                    class="text-xs font-semibold whitespace-nowrap tabular-nums"
                    [class]="allSaved() ? 'text-emerald-700' : 'text-gray-600'"
                  >
                    {{ n(draftCount()) }} de {{ n(closings().length) }}
                    {{ closings().length === 1 ? 'fecho' : 'fechos' }}
                  </span>
                </div>
              </div>

              <!-- Os cabeçalhos das duas colunas só existem lado a lado; empilhado,
                   cada cartão já diz de que lado é («Fecho de…», «Crédito de…»). -->
              <div
                class="mt-3 hidden grid-cols-[minmax(0,1fr)_1.25rem_minmax(0,1fr)] gap-x-2 text-gray-400 sm:grid"
              >
                <span [class]="th">Portal SIMO</span>
                <span></span>
                <span [class]="th">Banka</span>
              </div>

              <ul class="mt-2 space-y-2 sm:mt-1.5">
                @for (closing of closings(); track closing.id) {
                  @let credit = pairOf(closing.id);
                  @let saved = isSaved(closing.id);
                  <li
                    class="grid grid-cols-1 items-stretch gap-x-2 gap-y-1.5 sm:grid-cols-[minmax(0,1fr)_1.25rem_minmax(0,1fr)]"
                  >
                    <div class="rounded-lg bg-gray-50/80 px-3 py-2 ring-1 ring-gray-100">
                      <p class="text-sm font-semibold whitespace-nowrap text-gray-900 tabular-nums">
                        {{ amount(closing.simoClosingTotal) }}<span [class]="mzn">MZN</span>
                      </p>
                      <p class="mt-0.5 text-2xs text-gray-400 tabular-nums">
                        Fecho de {{ date(closing.simoClosingDate) }} ·
                        {{ n(closing.operationNumber) }}
                        {{ closing.operationNumber === 1 ? 'operação' : 'operações' }}
                      </p>
                    </div>

                    <span class="hidden items-center justify-center sm:flex" aria-hidden="true">
                      <svg
                        lucideLink2
                        [size]="14"
                        [strokeWidth]="2.4"
                        [class]="
                          credit ? (saved ? 'text-emerald-500' : 'text-amber-500') : 'text-gray-200'
                        "
                      ></svg>
                    </span>

                    @if (credit) {
                      <!-- Duas cores, dois estados: âmbar ainda é só uma proposta,
                           verde está guardado. A etiqueta vai na linha do valor, para
                           a data e o prazo de crédito caberem numa linha só. -->
                      <div
                        class="rounded-lg px-3 py-2 ring-1"
                        [class]="
                          saved
                            ? 'bg-emerald-50/70 ring-emerald-200'
                            : 'bg-amber-50/70 ring-amber-200'
                        "
                      >
                        <div class="flex items-center gap-2">
                          <p
                            class="min-w-0 flex-1 text-sm font-semibold whitespace-nowrap text-gray-900 tabular-nums"
                          >
                            {{ amount(credit.amount) }}<span [class]="mzn">MZN</span>
                          </p>
                          <span
                            class="text-2xs font-bold tracking-wide whitespace-nowrap uppercase"
                            [class]="saved ? 'text-emerald-600' : 'text-amber-700'"
                          >
                            {{ saved ? 'Conciliado' : 'Proposto' }}
                          </span>
                          <button
                            type="button"
                            (click)="unlink(closing.id)"
                            [attr.aria-label]="
                              'Desligar o crédito do fecho de ' + date(closing.simoClosingDate)
                            "
                            class="-my-1 -mr-1.5 inline-flex size-6 shrink-0 items-center justify-center rounded-md text-gray-400 transition-colors hover:bg-white hover:text-gray-900"
                          >
                            <svg lucideX [size]="14" [strokeWidth]="2.4"></svg>
                          </button>
                        </div>
                        <p class="mt-0.5 text-2xs text-gray-400 tabular-nums">
                          Crédito de {{ credit.date ? date(credit.date) : 'data desconhecida' }}
                          @if (creditedAfter(closing, credit); as when) {
                            · {{ when }}
                          }
                        </p>
                      </div>
                    } @else {
                      @let candidates = candidatesFor(closing.id);
                      <!-- Sem par: os créditos do mesmo valor ali mesmo, para ligar
                           com um clique — o valor é o do fecho, por isso cada botão
                           só precisa de dizer a data. -->
                      <div
                        class="rounded-lg border border-dashed bg-white px-3 py-2"
                        [class]="candidates.length > 0 ? 'border-gray-300' : 'border-gray-200'"
                      >
                        @if (candidates.length > 0) {
                          <p class="text-2xs text-gray-500">
                            {{
                              candidates.length === 1
                                ? 'Há um crédito com este valor:'
                                : 'Há ' + n(candidates.length) + ' créditos com este valor:'
                            }}
                          </p>
                          <div class="mt-1.5 flex flex-wrap gap-1.5">
                            @for (movement of candidates; track movement.id) {
                              <button
                                type="button"
                                (click)="link(closing.id, movement.id)"
                                class="inline-flex items-center gap-1 rounded-md bg-white px-2 py-1 text-xs font-semibold text-gray-700 tabular-nums shadow-xs ring-1 ring-gray-300 transition-colors hover:bg-emerald-50 hover:text-emerald-700 hover:ring-emerald-300"
                              >
                                <svg lucidePlus [size]="12" [strokeWidth]="2.6"></svg>
                                {{ movement.date ? date(movement.date) : 'Sem data' }}
                              </button>
                            }
                          </div>
                        } @else if (hasSameValue(closing)) {
                          <p class="py-1 text-xs text-gray-400">
                            O crédito com este valor já está ligado a outro fecho.
                          </p>
                        } @else {
                          <p class="py-1 text-xs text-gray-400">
                            Sem crédito com este valor no Banka.
                          </p>
                        }
                      </div>
                    }
                  </li>
                }
              </ul>

              @if (leftoverMovements().length > 0) {
                <!-- Os créditos que nenhum fecho levou: dinheiro que o Banka creditou
                     sem fecho correspondente na SIMO. Não se sabe porquê — outro
                     período que cai na mesma chave, ou um fecho que falta no export
                     —, e por isso a âmbar: alguém tem de o analisar, e o caso fica
                     aberto até lá. -->
                <div class="mt-3 rounded-lg bg-amber-50/70 px-3 py-2.5 ring-1 ring-amber-200">
                  <p class="text-2xs font-bold tracking-wider text-amber-800 uppercase">
                    Créditos do Banka sem fecho na SIMO · {{ n(leftoverMovements().length) }}
                  </p>
                  <ul class="mt-1 divide-y divide-amber-100">
                    @for (movement of leftoverMovements(); track movement.id) {
                      <li class="flex items-baseline justify-between gap-3 py-1.5 text-xs">
                        <span class="text-gray-600 tabular-nums">
                          Crédito de {{ movement.date ? date(movement.date) : 'data desconhecida' }}
                        </span>
                        <span class="font-semibold whitespace-nowrap text-gray-900 tabular-nums">
                          {{ amount(movement.amount) }}<span [class]="mzn">MZN</span>
                        </span>
                      </li>
                    }
                  </ul>
                  <p class="mt-1 text-2xs text-amber-800">
                    Nenhum fecho desta chave tem este valor. Confirme de onde vem o crédito — o caso
                    fica aberto para o tratar pela fase e pelo e-Ticket.
                  </p>
                </div>
              }

              @if (laterMovements().length > 0) {
                <!-- Sobram também, mas são de depois do último dia do intervalo: o
                     fecho deles está no intervalo seguinte. Mostram-se para não
                     parecer que desapareceram; não contam, nem seguram o caso. -->
                <div class="mt-3 rounded-lg bg-gray-50 px-3 py-2.5 ring-1 ring-gray-200">
                  <p class="text-2xs font-bold tracking-wider text-gray-500 uppercase">
                    Créditos depois do intervalo · {{ n(laterMovements().length) }}
                  </p>
                  <ul class="mt-1 divide-y divide-gray-100">
                    @for (movement of laterMovements(); track movement.id) {
                      <li class="flex items-baseline justify-between gap-3 py-1.5 text-xs">
                        <span class="text-gray-500 tabular-nums">
                          Crédito de {{ date(movement.date!) }}
                        </span>
                        <span class="font-semibold whitespace-nowrap text-gray-600 tabular-nums">
                          {{ amount(movement.amount) }}<span [class]="mzn">MZN</span>
                        </span>
                      </li>
                    }
                  </ul>
                  <p class="mt-1 text-2xs text-gray-500">
                    São de depois de {{ date(data()!.periodEnd) }}, o último dia desta execução — o
                    fecho está no intervalo seguinte. Não contam como crédito sem fecho.
                  </p>
                </div>
              }

              @if (matchesDirty() || allSaved() || canReset()) {
                <!-- O rodapé diz o que o botão vai fazer antes de se carregar nele. -->
                <div
                  class="mt-3.5 flex flex-wrap items-center justify-end gap-2 border-t border-gray-100 pt-3"
                >
                  <p class="mr-auto text-xs font-medium">
                    @if (matchesDirty()) {
                      @if (allDrafted() && leftoverMovements().length > 0) {
                        <span class="text-amber-700">
                          Ao confirmar, os fechos conferem — o caso fica aberto pelo crédito sem
                          fecho.
                        </span>
                      } @else if (allDrafted()) {
                        <span class="text-emerald-700"
                          >Ao confirmar, o caso fica regularizado.</span
                        >
                      } @else {
                        <span class="text-amber-700">
                          {{ n(closings().length - draftCount()) }}
                          {{
                            closings().length - draftCount() === 1
                              ? 'fecho fica por conciliar'
                              : 'fechos ficam por conciliar'
                          }}.
                        </span>
                      }
                    } @else if (allSaved() && leftoverMovements().length > 0) {
                      <span class="text-amber-700">
                        Fechos conciliados — falta analisar o crédito sem fecho.
                      </span>
                    } @else if (allSaved()) {
                      <span class="inline-flex items-center gap-1 text-emerald-700">
                        <svg lucideCheck [size]="14" [strokeWidth]="2.6"></svg>
                        Conciliação concluída.
                      </span>
                    }
                  </p>
                  @if (canReset()) {
                    <button
                      type="button"
                      (click)="resetDraft()"
                      class="rounded-lg px-3 py-2 text-sm font-semibold text-gray-600 transition-colors hover:bg-gray-100 hover:text-gray-900"
                    >
                      Repor
                    </button>
                  }
                  @if (matchesDirty()) {
                    <button
                      type="button"
                      (click)="confirmMatches(pendingCase)"
                      class="inline-flex items-center gap-1.5 rounded-lg bg-moza-700 px-3.5 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-moza-800"
                    >
                      <svg lucideCheck [size]="15" [strokeWidth]="2.6"></svg>
                      Confirmar conciliação
                    </button>
                  }
                </div>
              }
            </section>
          } @else {
            <!-- Fundo neutro: os dois lados levam tons diferentes, não cores — não há bom/mau aqui. -->
            <section class="mt-4 rounded-xl bg-gray-50/80 px-4 py-3.5 ring-1 ring-gray-100">
              <h3 [class]="sectionTitle">
                Portal SIMO ·
                {{
                  closings().length === 1
                    ? 'o fecho apurado'
                    : n(closings().length) + ' fechos apurados'
                }}
              </h3>

              <!-- Scroll próprio em vez de espremer as colunas: o painel ocupa a
                   largura toda num ecrã estreito, e um montante partido não se lê. -->
              <div class="mt-2.5 overflow-x-auto">
                <table class="w-full min-w-sm border-collapse text-sm">
                  <thead>
                    <tr class="border-b border-gray-100 text-gray-400">
                      <th scope="col" [class]="th + ' py-2 pr-3 text-left'">Data Fecho</th>
                      <th scope="col" [class]="th + ' px-3 py-2 text-right'">Nº Operaç.</th>
                      <th scope="col" [class]="th + ' py-2 pl-3 text-right'">Total do fecho</th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (closing of closings(); track closing.id) {
                      <!-- O fecho clicado assinala-se pelo fundo branco, sem marca à frente da data. -->
                      <tr
                        class="border-b border-gray-100/80 last:border-b-0"
                        [class]="closing.id === d.id ? 'bg-white text-gray-900' : 'text-gray-600'"
                      >
                        <td class="py-2.5 pr-3 tabular-nums">
                          {{ date(closing.simoClosingDate) }}
                        </td>
                        <td class="px-3 py-2.5 text-right tabular-nums text-gray-400">
                          {{ closing.operationNumber }}
                        </td>
                        <td class="py-2.5 pl-3 text-right">
                          <span class="font-semibold whitespace-nowrap tabular-nums text-gray-900">
                            {{ amount(closing.simoClosingTotal) }}<span [class]="mzn">MZN</span>
                          </span>
                        </td>
                      </tr>
                    }
                  </tbody>
                  <!-- A soma vive no pé da coluna que soma, alinhada para se conferir a conta. -->
                  <tfoot>
                    <tr class="border-t border-gray-200">
                      <td class="pt-2.5 pr-3 text-xs text-gray-500" colspan="2">Total apurado</td>
                      <td class="pt-2.5 pl-3 text-right">
                        <span class="font-semibold whitespace-nowrap tabular-nums text-gray-900">
                          {{ amount(simoTotal()) }}<span [class]="mzn">MZN</span>
                        </span>
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </section>

            <section class="mt-4 rounded-xl bg-moza-50 px-4 py-3.5 ring-1 ring-moza-200">
              <h3 [class]="sectionTitle">
                Banka ·
                {{
                  movements().length === 0
                    ? 'sem crédito'
                    : n(movements().length) +
                      ' ' +
                      (movements().length === 1 ? 'movimento creditado' : 'movimentos creditados')
                }}
              </h3>

              @if (sharedDescription(); as shared) {
                <p class="mt-1 truncate text-xs text-gray-400">{{ shared }}</p>
              }

              @if (movements().length === 0) {
                <p class="mt-2.5 rounded-xl bg-white/70 px-4 py-3 text-sm text-gray-500">
                  Não há nenhum movimento do Banka com esta chave.
                  @if (d.bankaClosingTotal !== null) {
                    O crédito da chave está apurado em
                    <b class="text-gray-900">{{ amount(d.bankaClosingTotal) }} MZN</b>, mas as
                    parcelas não foram guardadas — é uma execução anterior à versão que as passou a
                    registar. Volte a correr a validação para as ver.
                  }
                </p>
              } @else {
                <div class="mt-2.5 overflow-x-auto">
                  <table class="w-full min-w-md border-collapse text-sm">
                    <thead>
                      <tr class="border-b border-moza-200 text-gray-400">
                        <th scope="col" [class]="th + ' py-2 pr-3 text-left'">Data Crédito</th>
                        <th scope="col" [class]="th + ' px-3 py-2 text-left'">Creditado</th>
                        @if (!sharedDescription()) {
                          <th scope="col" [class]="th + ' px-3 py-2 text-left'">Descritivo</th>
                        }
                        <th scope="col" [class]="th + ' py-2 pl-3 text-right'">Valor</th>
                      </tr>
                    </thead>
                    <tbody>
                      @for (movement of movements(); track movement.id) {
                        <tr class="border-b border-moza-100 text-gray-600 last:border-b-0">
                          <td class="py-2.5 pr-3 tabular-nums">
                            {{ movement.date ? date(movement.date) : '—' }}
                          </td>
                          <td class="px-3 py-2.5 whitespace-nowrap">
                            @if (whenCredited(movement.date); as when) {
                              {{ when }}
                            } @else {
                              <span class="text-gray-300">—</span>
                            }
                          </td>
                          @if (!sharedDescription()) {
                            <td class="px-3 py-2.5">
                              <span class="block max-w-64 truncate text-sm">
                                {{ movement.description || '—' }}
                              </span>
                            </td>
                          }
                          <td class="py-2.5 pl-3 text-right">
                            <span
                              class="font-semibold whitespace-nowrap tabular-nums text-gray-900"
                            >
                              {{ amount(movement.amount) }}<span [class]="mzn">MZN</span>
                            </span>
                          </td>
                        </tr>
                      }
                    </tbody>
                    <tfoot>
                      <tr class="border-t border-moza-200">
                        <td
                          class="pt-2.5 pr-3 text-xs text-gray-500"
                          [attr.colspan]="sharedDescription() ? 2 : 3"
                        >
                          Total creditado
                        </td>
                        <td class="pt-2.5 pl-3 text-right">
                          <span class="font-semibold whitespace-nowrap tabular-nums text-gray-900">
                            {{ amount(bankaTotal()) }}<span [class]="mzn">MZN</span>
                          </span>
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              }
            </section>
          }
        }
      </div>
    </aside>
  `,
})
export class KeyDetailPanelComponent {
  private readonly api = inject(ReconciliationApi);

  readonly executionId = input.required<string>();
  /** Para calcular a data limite do caso, se a chave tiver um. */
  readonly settings = input.required<SlaSettings>();
  /**
   * O fecho clicado — dá a identidade e fica assinalado na lista da SIMO.
   * Quando se abre a partir de um caso (a chave inteira, não um fecho), é uma
   * vista construída sem tipo de fecho real — `closingType` abaixo corrige-se
   * sozinho assim que os fechos verdadeiros da chave chegam.
   */
  readonly detail = input.required<ClosingDetail>();
  readonly closed = output<void>();
  /** Sobe até à página, que é quem chama a API e recalcula o `summary`. */
  readonly updated = output<CasePatch>();
  /** Os pares da conciliação fecho a fecho — o mesmo caminho do `updated`. */
  readonly reconciled = output<CaseMatches>();

  protected readonly data = signal<KeyBreakdown | null>(null);
  protected readonly error = signal<string | null>(null);

  protected readonly meta = 'inline-flex items-baseline gap-1.5 whitespace-nowrap';
  protected readonly metaValue = 'font-semibold text-gray-700 tabular-nums';
  protected readonly mzn = 'ml-1 text-[0.7em] font-normal text-gray-400';
  protected readonly th = 'text-2xs font-bold tracking-wider uppercase';
  protected readonly sectionTitle = 'text-2xs font-bold tracking-wider text-gray-400 uppercase';
  protected readonly totalLabel = 'text-2xs font-bold tracking-wider text-gray-400 uppercase';
  protected readonly totalValue = 'mt-1 text-base font-bold tabular-nums';
  protected readonly fieldLabel = 'text-2xs font-bold tracking-wider text-gray-400 uppercase';
  protected readonly fieldValue = 'mt-0.5 truncate text-sm font-semibold text-gray-900';

  protected readonly closings = computed(() => this.data()?.closings ?? []);
  protected readonly movements = computed(() => this.data()?.movements ?? []);
  protected readonly simoTotal = computed(() => this.detail().simoKeyTotal);

  /**
   * Sem parcelas guardadas (execução anterior à migração) cai-se no total já
   * apurado da chave: o apuramento continua certo, só não há detalhe para somar.
   */
  protected readonly bankaTotal = computed(() => {
    const movements = this.movements();
    if (movements.length > 0) {
      return movements.reduce((total, movement) => total + movement.amount, 0);
    }
    return this.detail().bankaClosingTotal ?? 0;
  });

  protected readonly difference = computed(() => this.bankaTotal() - this.simoTotal());

  /** Igual em todos os movimentos: mostra-se uma vez no topo e a coluna desaparece. */
  protected readonly sharedDescription = computed(() => {
    const descriptions = new Set(this.movements().map((movement) => movement.description ?? ''));
    return descriptions.size === 1 ? [...descriptions][0] || null : null;
  });

  /** Só se pode datar o prazo com um único fecho na chave — com vários, não se sabe qual é qual. */
  private readonly soleClosingDate = computed(() => {
    const closings = this.closings();
    return closings.length === 1 ? closings[0].simoClosingDate : undefined;
  });

  /** Prefere o fecho real, assim que carrega — a vista construída a partir de
   *  um caso não sabe o tipo de fecho da chave. */
  protected readonly closingType = computed(
    () => this.data()?.closings[0]?.closingType ?? this.detail().closingType,
  );

  protected readonly chip = computed(() => STATE_CHIP[this.detail().validation]);
  protected readonly dot = computed(() => STATE_DOT[this.detail().validation]);
  protected readonly stateLabel = computed(() => STATE_LABEL[this.detail().validation]);

  constructor() {
    // Recarrega a cada chave: abrir outro fecho reutiliza o painel já montado.
    effect((onCleanup) => {
      const executionId = this.executionId();
      const key = this.detail().key;

      let cancelled = false;
      onCleanup(() => {
        cancelled = true;
      });

      this.data.set(null);
      this.error.set(null);

      void this.api
        .getKeyBreakdown(executionId, key)
        .then((result) => {
          if (!cancelled) this.data.set(result);
        })
        .catch((problem: unknown) => {
          if (cancelled) return;
          this.error.set(
            problem instanceof Error ? problem.message : 'Não foi possível abrir o fecho.',
          );
        });
    });

    // Tranca o scroll da página (compensando a largura da barra em padding, para
    // o conteúdo não saltar) enquanto o painel está aberto.
    const { body } = document;
    const scrollbar = window.innerWidth - document.documentElement.clientWidth;
    const previous = { overflow: body.style.overflow, paddingRight: body.style.paddingRight };
    body.style.overflow = 'hidden';
    if (scrollbar > 0) body.style.paddingRight = `${scrollbar}px`;

    inject(DestroyRef).onDestroy(() => {
      body.style.overflow = previous.overflow;
      body.style.paddingRight = previous.paddingRight;
    });
  }

  protected whenCredited(creditIso: string | null): string | null {
    return creditedWhen(this.soleClosingDate(), creditIso);
  }

  /** Fixado à montagem, como na tabela: o painel não muda de dia enquanto está aberto. */
  private readonly today = startOfToday();

  protected readonly sourceLabel = SOURCE_LABEL;
  protected readonly statuses = CASE_STATUSES;
  protected readonly statusLabel = CASE_STATUS_LABEL;
  protected readonly statusWait = CASE_STATUS_WAIT;
  protected readonly statusDot = CASE_STATUS_DOT;

  /** O que está no formulário e ainda não foi guardado. Volta ao do caso sempre que ele muda. */
  protected readonly draftStatus = linkedSignal<CaseStatus>(
    () => this.data()?.case?.status ?? 'pending',
  );
  protected readonly draftETicket = linkedSignal(() => this.data()?.case?.eTicket ?? '');
  protected readonly eTicketError = computed(() => eTicketProblem(this.draftETicket()));
  protected readonly maxETicket = MAX_E_TICKET_LENGTH;

  protected readonly dirty = computed(() => {
    const item = this.data()?.case;
    if (!item) return false;
    return (
      this.draftStatus() !== item.status ||
      (this.draftETicket().trim() || null) !== (item.eTicket ?? null)
    );
  });

  protected discard(item: PendingCase): void {
    this.draftStatus.set(item.status);
    this.draftETicket.set(item.eTicket ?? '');
  }

  /** Um pedido só, com o que mudou — estado, e-Ticket, ou os dois. */
  protected save(item: PendingCase): void {
    if (!this.dirty() || this.eTicketError()) return;
    const status = this.draftStatus();
    const eTicket = this.draftETicket().trim() || null;

    const patch: CasePatch['patch'] = {};
    if (status !== item.status) patch.status = status;
    if (eTicket !== (item.eTicket ?? null)) patch.eTicket = eTicket;
    this.updated.emit({ caseId: item.id, patch });

    // O painel tem a sua própria cópia da chave (foi ele que a foi buscar), por
    // isso acompanha a mudança em vez de esperar por ela — como a tabela faz.
    // Se o pedido falhar, quem o diz é o toast de erro da página.
    const current = this.data();
    if (!current?.case) return;
    this.data.set({
      ...current,
      case: {
        ...current.case,
        eTicket,
        status,
        resolvedAt:
          status === 'resolved' ? (current.case.resolvedAt ?? toIsoDate(this.today)) : null,
        statusSince: patch.status ? toIsoDate(this.today) : current.case.statusSince,
      },
    });
  }

  // ─── Conciliação ─────────────────────────────────────────────────────────

  /** Só períodos duplicados com créditos: sem créditos não há par possível. */
  protected readonly canMatch = computed(
    () =>
      // Pelo caso e não pelo fecho: um fecho já conciliado passa a «confere», e
      // tem de continuar a abrir o quadro — para se ver o par, e o poder desfazer.
      (this.detail().validation === 'duplicated' || this.data()?.case?.type === 'duplicated') &&
      this.movements().length > 0,
  );

  private readonly savedDraft = computed(() => toDraft(this.data()?.matches ?? []));

  /**
   * De onde o ecrã parte: o que está guardado, ou — se nada estiver — os pares
   * que se fazem só pelo valor, já propostos. O caso comum é confirmar.
   */
  private readonly initialDraft = computed(() => {
    const saved = this.savedDraft();
    return Object.keys(saved).length > 0 ? saved : toDraft(this.data()?.suggestedMatches ?? []);
  });

  /** O que está ligado no ecrã. Volta ao ponto de partida sempre que ele muda. */
  protected readonly draftMatches = linkedSignal<MatchDraft>(() => this.initialDraft());

  protected readonly draftCount = computed(() => Object.keys(this.draftMatches()).length);
  protected readonly progress = computed(() => {
    const total = this.closings().length;
    return total > 0 ? (this.draftCount() / total) * 100 : 0;
  });
  protected readonly allDrafted = computed(
    () => this.closings().length > 0 && this.draftCount() === this.closings().length,
  );
  protected readonly allSaved = computed(
    () =>
      this.closings().length > 0 &&
      Object.keys(this.savedDraft()).length === this.closings().length,
  );
  protected readonly matchesDirty = computed(
    () => !sameDraft(this.draftMatches(), this.savedDraft()),
  );
  protected readonly canReset = computed(
    () => !sameDraft(this.draftMatches(), this.initialDraft()),
  );

  private readonly movementById = computed(
    () => new Map(this.movements().map((movement) => [movement.id, movement])),
  );

  /** Os créditos que nenhum fecho levou — aparecem uma vez, no fim do quadro. */
  private readonly unusedMovements = computed(() => {
    const used = new Set(Object.values(this.draftMatches()));
    return this.movements().filter((movement) => !used.has(movement.id));
  });

  /** Os que contam: do intervalo da execução — seguram o caso aberto. */
  protected readonly leftoverMovements = computed(() => {
    const periodEnd = this.data()?.periodEnd;
    return periodEnd
      ? this.unusedMovements().filter((movement) => withinPeriod(movement, periodEnd))
      : this.unusedMovements();
  });

  /** Os de depois do último dia — do intervalo seguinte; mostram-se, mas não contam. */
  protected readonly laterMovements = computed(() => {
    const periodEnd = this.data()?.periodEnd;
    return periodEnd
      ? this.unusedMovements().filter((movement) => !withinPeriod(movement, periodEnd))
      : [];
  });

  protected pairOf(closingId: string): CreditMovement | undefined {
    const movementId = this.draftMatches()[closingId];
    return movementId ? this.movementById().get(movementId) : undefined;
  }

  /** O par que está no ecrã é o que está guardado — «Conciliado», e não «Proposto». */
  protected isSaved(closingId: string): boolean {
    const movementId = this.draftMatches()[closingId];
    return movementId !== undefined && this.savedDraft()[closingId] === movementId;
  }

  protected hasSameValue(closing: ClosingDetail): boolean {
    return this.movements().some((movement) =>
      sameAmount(movement.amount, closing.simoClosingTotal),
    );
  }

  /** Os créditos do mesmo valor que nenhum outro fecho levou. Um crédito não paga dois fechos. */
  protected candidatesFor(closingId: string): CreditMovement[] {
    const closing = this.closings().find((item) => item.id === closingId);
    if (!closing) return [];
    const taken = new Set(Object.values(this.draftMatches()));
    return this.movements().filter(
      (movement) =>
        sameAmount(movement.amount, closing.simoClosingTotal) && !taken.has(movement.id),
    );
  }

  /** «3 dias depois» — do fecho até ao crédito que o paga, o que ajuda a decidir. */
  protected creditedAfter(closing: ClosingDetail, credit: CreditMovement): string | null {
    return creditedWhen(closing.simoClosingDate, credit.date);
  }

  protected link(closingId: string, movementId: string): void {
    this.draftMatches.update((draft) => ({ ...draft, [closingId]: movementId }));
  }

  protected unlink(closingId: string): void {
    this.draftMatches.update((draft) => {
      const next: Record<string, string> = { ...draft };
      delete next[closingId];
      return next;
    });
  }

  protected resetDraft(): void {
    this.draftMatches.set(this.initialDraft());
  }

  /**
   * Um pedido só, com todos os pares — substituem os que havia.
   *
   * Acompanha a mudança em vez de esperar por ela, como o `save` do caso: se
   * todos os fechos ficam com par, o servidor regulariza o caso, e o painel
   * mostra-o já. Se o pedido falhar, quem o diz é o toast da página.
   */
  protected confirmMatches(item: PendingCase): void {
    if (!this.matchesDirty()) return;
    const draft = this.draftMatches();
    const matches = toMatches(draft);
    this.reconciled.emit({ caseId: item.id, matches });

    const current = this.data();
    if (!current?.case) return;
    // A regra do servidor (`settles_case`): todos os fechos com par, e nenhum
    // crédito do intervalo a sobrar — um crédito sem fecho deixa o caso aberto.
    const used = new Set(Object.values(draft));
    const complete =
      current.closings.length > 0 &&
      current.closings.every((closing) => closing.id in draft) &&
      current.movements.every(
        (movement) => used.has(movement.id) || !withinPeriod(movement, current.periodEnd),
      );
    const resolves = complete && current.case.status !== 'resolved';
    const today = toIsoDate(this.today);
    this.data.set({
      ...current,
      matches,
      case: resolves
        ? { ...current.case, status: 'resolved', resolvedAt: today, statusSince: today }
        : current.case,
    });
  }

  protected capitalize = (text: string) => text.charAt(0).toUpperCase() + text.slice(1);

  /** Dias no estado actual — o relógio recomeça a cada mudança de estado. */
  protected daysInStatus = (item: PendingCase): number =>
    daysBetween(parseIsoDate(item.statusSince), this.today);
  protected slaOf = (item: PendingCase): SlaView => slaOf(item, this.settings(), this.today);
  protected slaPhrase = slaPhrase;
  protected slaTone = slaToneOf;
  protected slaDotTone = slaDotOf;

  protected caseStatus = (status: CaseStatus) => CASE_STATUS_LABEL[status];
  protected amount = formatAmount;
  protected signed = formatSignedAmount;
  protected date = formatDate;
  protected dateValue = formatDateValue;
  protected dayCount = formatDayCount;
  protected n = (value: number) => numberFormatter.format(value);
}
