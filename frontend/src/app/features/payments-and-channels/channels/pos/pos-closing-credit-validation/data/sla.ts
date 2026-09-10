/**
 * O prazo de tratamento de um caso — data limite, atraso e estado.
 *
 * Espelha o `domain/sla.py` do serviço, como o `models.ts` espelha os schemas:
 * a data limite é a data do fecho mais o prazo, e mais nada. A conta fica deste
 * lado porque só aqui se sabe que dia é hoje — o servidor corre a UTC, e a data
 * local do operador é a data de negócio (Moçambique não muda de hora).
 *
 * **Não confundir com prazo de crédito.** Isto conta o tempo que um caso já
 * divergente leva por tratar; não decide validação nenhuma.
 */
import { daysBetween, formatDayCount, parseIsoDate } from '../../../../../../shared/format';
import type { CaseDateSource, PendingCase, SlaSettings } from './models';

/** Como se nomeia cada lado ao operador. */
export const SOURCE_LABEL: Record<CaseDateSource, string> = {
  simo: 'SIMO',
  banka: 'Banka',
};

/** O que o ecrã assume enquanto as definições não chegam do servidor. */
export const DEFAULT_SLA: SlaSettings = {
  caseSlaDays: 7,
  caseWarningDays: 3,
  updatedAt: null,
  updatedBy: null,
};

export const MAX_SLA_DAYS = 365;

export type SlaState = 'on-track' | 'due-soon' | 'overdue' | 'settled';

export interface SlaView {
  readonly state: SlaState;
  readonly deadline: Date;
  /** Dias até à data limite: negativo quando já passou. */
  readonly remaining: number;
  /** Dias desde a data do fecho até hoje (ou até à regularização). */
  readonly age: number;
}

/** Hoje à meia-noite, para as contas serem em dias inteiros e não em horas. */
export function startOfToday(): Date {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth(), now.getDate());
}

export function deadlineOf(firstDate: string, slaDays: number): Date {
  const deadline = parseIsoDate(firstDate);
  deadline.setDate(deadline.getDate() + slaDays);
  return deadline;
}

/**
 * O relógio pára ao regularizar: um caso fechado a tempo não pode ficar
 * vermelho na semana seguinte. Em análise continua a contar — o trabalho ainda
 * não está feito.
 */
export function slaOf(item: PendingCase, settings: SlaSettings, today: Date): SlaView {
  const first = parseIsoDate(item.firstDate);
  const deadline = deadlineOf(item.firstDate, settings.caseSlaDays);
  const settled = item.status === 'resolved';
  const reference = settled && item.resolvedAt ? parseIsoDate(item.resolvedAt) : today;

  const remaining = daysBetween(reference, deadline);
  const age = daysBetween(first, reference);

  if (settled) return { state: 'settled', deadline, remaining, age };
  if (remaining < 0) return { state: 'overdue', deadline, remaining, age };
  if (remaining <= settings.caseWarningDays) return { state: 'due-soon', deadline, remaining, age };
  return { state: 'on-track', deadline, remaining, age };
}

/** Regularizado depois da data limite: tratado, mas fora de horas. */
export function isLate(sla: SlaView): boolean {
  return sla.state === 'settled' && sla.remaining < 0;
}

/** O que se diz sobre a data limite — a leitura principal. */
export function slaPhrase(sla: SlaView): string {
  if (sla.state === 'settled') return isLate(sla) ? 'Tratado fora do prazo' : 'Tratado a tempo';
  if (sla.remaining < 0) return `${formatDayCount(-sla.remaining)} em atraso`;
  if (sla.remaining === 0) return 'Vence hoje';
  return `Faltam ${formatDayCount(sla.remaining)}`;
}

/** Quanto tempo levou, ou leva, desde a primeira data da chave. */
export function slaAgePhrase(sla: SlaView): string {
  return sla.state === 'settled'
    ? `levou ${formatDayCount(sla.age)}`
    : `em aberto há ${formatDayCount(sla.age)}`;
}

export const SLA_LABEL: Record<SlaState, string> = {
  'on-track': 'Dentro do prazo',
  'due-soon': 'Prestes a vencer',
  overdue: 'Em atraso',
  settled: 'Regularizado',
};

export const SLA_DOT: Record<SlaState, string> = {
  'on-track': 'bg-gray-300',
  'due-soon': 'bg-amber-500',
  overdue: 'bg-alert-500',
  settled: 'bg-emerald-500',
};

/** Só a cor do texto: a pastilha cheia da coluna «Tipo» já chega por linha. */
export const SLA_TEXT: Record<SlaState, string> = {
  'on-track': 'text-gray-500',
  'due-soon': 'text-amber-700',
  overdue: 'text-alert-700',
  settled: 'text-emerald-700',
};

/** Verde só quando foi mesmo tratado a tempo — senão o âmbar diz a verdade. */
export function slaToneOf(sla: SlaView): string {
  return isLate(sla) ? SLA_TEXT['due-soon'] : SLA_TEXT[sla.state];
}

export function slaDotOf(sla: SlaView): string {
  return isLate(sla) ? SLA_DOT['due-soon'] : SLA_DOT[sla.state];
}
