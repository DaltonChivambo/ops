/**
 * Tipos do módulo "Validação de Crédito de Valores de Fecho" (PDD 1.1, Moza Banco / DOP).
 * Espelham 1:1 o JSON da API. Identificadores em inglês; o português fica no conteúdo e nas rotas.
 * Glossário face ao PDD:
 *   fecho / fechos SIMO ............. closing / simoClosings
 *   créditos Banka · lista de POS ... bankaCredits · posList
 *   comerciante · nº conta · período  merchant · accountNumber · period
 *   chave (posId + período % 1000) .. key
 *   validação: confere/incorrecto/N-D validation: match/mismatch/missing
 *   diferença apurada ............... difference
 *   caso pendente ................... PendingCase
 *   estado: pendente/em análise/regularizado  status: pending/in-review/resolved
 *   data de regularização ........... resolvedAt
 *   tipo de fecho ................... closingType
 */

export type ClosingType = 'D' | 'D+1' | 'n.a';

/** Confere · incorrecto · não creditado · zerado (0,00) · períodos duplicados. */
export type Validation = 'match' | 'mismatch' | 'missing' | 'zero' | 'duplicated';

export type CaseStatus = 'pending' | 'in-review' | 'resolved';

export type CaseType = 'missing' | 'mismatch';

export type UploadSlotId = 'posList' | 'simoClosings' | 'bankaCredits';

/** Uma linha da folha "Detalhes Validacao" — um fecho registado na SIMO. */
export interface ClosingDetail {
  id: string;
  posId: string;
  merchant: string;
  accountNumber: string;
  period: number;
  key: string;
  simoClosingDate: string; // ISO
  operationNumber: number;
  /** Só este fecho — não é o termo que a `difference` compara. */
  simoClosingTotal: number; // MZN
  /** Soma dos fechos SIMO da chave; é este que fecha com `bankaClosingTotal`. */
  simoKeyTotal: number;
  closingDescription: string | null;
  bankaCreditDate: string | null;
  /** Soma dos créditos Banka da chave; null quando não creditado. */
  bankaClosingTotal: number | null;
  closingType: ClosingType;
  /** Calculada ao nível da chave (soma SIMO vs soma Banka). */
  validation: Validation;
  /** somaBanka − somaSimo da chave; null quando não creditado. */
  difference: number | null;
}

/** Um movimento de crédito do Banka atribuído a uma chave — a parcela do total. */
export interface CreditMovement {
  id: string;
  key: string;
  date: string | null; // ISO
  amount: number; // MZN
  description: string | null;
}

/** Os dois lados de uma chave — o que o painel de detalhe de um fecho mostra. */
export interface KeyBreakdown {
  key: string;
  /** Todos os fechos SIMO desta chave (mais do que um = períodos duplicados). */
  closings: ClosingDetail[];
  /** Vazio nas execuções anteriores à migração que passou a guardá-los. */
  movements: CreditMovement[];
  case: PendingCase | null;
}

/** Caso de divergência para análise/regularização pelo operador. */
export interface PendingCase {
  id: string;
  key: string;
  posId: string;
  period: number;
  merchant: string;
  accountNumber: string;
  simoAmount: number;
  bankaAmount: number; // 0 quando não creditado
  type: CaseType;
  eTicket: string | null;
  status: CaseStatus;
  resolvedAt: string | null;
}

/** Indicadores do dashboard operacional (PDD §4.2.1). */
export interface ClosingSummary {
  processed: number;
  matched: number;
  divergent: number;
  validationRate: number; // 0–100, 1 decimal
  divergenceAmount: number; // MZN
  openCases: number;
  resolvedCases: number;
  missingCount: number;
  mismatchCount: number;
  /** Fechos de valor 0,00 — sem crédito a esperar do Banka; fora dos casos. */
  zeroClosings: number;
  /** Fechos em chaves com >1 fecho (período repetido/colidido); análise manual. */
  duplicatedPeriods: number;
  /** Linhas repetidas no export da SIMO, descartadas antes de somar. */
  duplicatesDiscarded: number;
  /** Chaves que agregam >1 período por colisão em `período % 1000` (falsa divergência). */
  keyCollisions: number;
  /** POS com fechos mas sem cadastro na Lista de POS (comerciante "—"). */
  unregisteredPos: number;
  simoAmountMatched: number;
  bankaAmountMatched: number;
  simoAmountMismatched: number;
  bankaAmountMismatched: number;
  simoAmountMissing: number;
  /** Somas das chaves com períodos duplicados — retido à espera de análise. O
   *  Banka duplica nestas chaves tal como a SIMO, por isso há crédito feito. */
  simoAmountDuplicated: number;
  bankaAmountDuplicated: number;
}

/** Uma execução persistida. Os detalhes vêm à parte, paginados. */
export interface ValidationResult {
  executionId: string;
  executedAt: string;
  periodStart: string;
  periodEnd: string;
  reportName: string; // "FECHO_POS_DOP 21 a 28 de Junho-2026"
  files: Record<UploadSlotId, string>;
  summary: ClosingSummary;
  cases: PendingCase[];
}

export interface DetailCounts {
  all: number;
  match: number;
  mismatch: number;
  missing: number;
  zero: number;
  duplicated: number;
}

/** Página da tabela de reconciliação — filtrada e contada no servidor. */
export interface DetailsPage {
  items: ClosingDetail[];
  total: number;
  page: number;
  perPage: number;
  counts: DetailCounts;
}

export interface DetailsQuery {
  page?: number;
  perPage?: number;
  /** Classes a mostrar. `null`/ausente = todas; lista vazia = nenhuma. */
  validation?: Validation[] | null;
  q?: string;
}

/** Fases grosseiras: o upload e a execução são um único round-trip HTTP. */
export type ProgressPhase = 'upload' | 'reconciliation';

export type ExecutionOutcome =
  { ok: true; result: ValidationResult } | { ok: false; message: string }; // exceção de negócio do PDD
