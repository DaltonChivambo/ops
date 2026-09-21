import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { ApiError } from '../../../../../../core/http/api-error';
import { environment } from '../../../../../../../environments/environment';
import type {
  CaseMatches,
  CaseReconciliation,
  CaseStatus,
  ClosingMatch,
  ClosingSummary,
  DetailsPage,
  DetailsQuery,
  ExecutionOutcome,
  KeyBreakdown,
  PendingCase,
  ReconciliationBatch,
  ReconciliationCandidate,
  SlaSettings,
  UploadSlotId,
  Validation,
  ValidationResult,
} from './models';

const SLOTS: readonly UploadSlotId[] = ['posList', 'simoClosings', 'bankaCredits'];

const EMPTY_PAGE: DetailsPage = {
  items: [],
  total: 0,
  page: 1,
  perPage: 50,
  counts: { all: 0, simoDuplicates: 0, match: 0, mismatch: 0, missing: 0, zero: 0, duplicated: 0 },
};

/**
 * Camada de dados do módulo — o parsing dos Excel e a reconciliação vivem no servidor.
 * `Promise` e não `Observable`: cada chamada tem um resultado só, sem fluxo nem cancelamento a aproveitar.
 */
@Injectable({ providedIn: 'root' })
export class ReconciliationApi {
  private readonly http = inject(HttpClient);
  private readonly base = environment.closingApiBase;

  /**
   * Envia os três ficheiros e devolve o resultado.
   *
   * As excepções de negócio do PDD (ficheiro errado, colunas em falta) voltam
   * como `{ok:false}` e não como excepção: são resposta esperada, e o ecrã
   * mostra-as ao operador. Só o inesperado sobe.
   */
  async runValidation(files: Record<UploadSlotId, File>): Promise<ExecutionOutcome> {
    const body = new FormData();
    for (const slot of SLOTS) body.append(slot, files[slot], files[slot].name);

    try {
      const result = await firstValueFrom(
        this.http.post<ValidationResult>(`${this.base}/execucoes`, body),
      );
      return { ok: true, result };
    } catch (error) {
      if (error instanceof ApiError) return { ok: false, message: error.message };
      throw error;
    }
  }

  /** `null` quando ainda não correu nenhuma validação (204 do servidor). */
  getLatestResult(): Promise<ValidationResult | null> {
    return firstValueFrom(this.http.get<ValidationResult | null>(`${this.base}/execucoes/ultima`));
  }

  async listDetails(executionId: string, query: DetailsQuery = {}): Promise<DetailsPage> {
    let params = new HttpParams();
    if (query.page !== undefined) params = params.set('page', query.page);
    if (query.perPage !== undefined) params = params.set('perPage', query.perPage);
    if (query.q) params = params.set('q', query.q);
    if (query.repeated && query.repeated !== 'all') params = params.set('repeated', query.repeated);

    const validation = serializeValidations(query.validation);
    if (validation !== null) params = params.set('validation', validation);

    const page = await firstValueFrom(
      this.http.get<DetailsPage | null>(`${this.base}/execucoes/${executionId}/detalhes`, {
        params,
      }),
    );
    return page ?? EMPTY_PAGE;
  }

  /**
   * Os dois lados de uma chave: os fechos da SIMO e os movimentos do Banka.
   *
   * A unidade é a chave e não o fecho — o crédito do Banka é da chave, um fecho
   * isolado não tem crédito próprio de que se possa falar.
   */
  getKeyBreakdown(executionId: string, key: string): Promise<KeyBreakdown | null> {
    const path = `${this.base}/execucoes/${executionId}/chaves/${encodeURIComponent(key)}`;
    return firstValueFrom(this.http.get<KeyBreakdown | null>(path));
  }

  updateCase(
    caseId: string,
    patch: { status?: CaseStatus; eTicket?: string | null },
  ): Promise<{ case: PendingCase; summary: ClosingSummary }> {
    return firstValueFrom(
      this.http.patch<{ case: PendingCase; summary: ClosingSummary }>(
        `${this.base}/casos/${caseId}`,
        patch,
      ),
    );
  }

  /**
   * Guarda os pares fecho ↔ crédito de um caso de períodos repetidos. Conciliar
   * todos os fechos regulariza o caso — é o servidor que o decide e o devolve.
   */
  reconcileCase(caseId: string, matches: readonly ClosingMatch[]): Promise<CaseReconciliation> {
    return firstValueFrom(
      this.http.put<CaseReconciliation>(`${this.base}/casos/${caseId}/conciliacao`, { matches }),
    );
  }

  /**
   * Manda contar, ou não, o dinheiro dos fechos repetidos da SIMO no apuramento.
   *
   * Não mexe em estados nem em casos — só nos montantes. Volta a execução
   * inteira porque é ela que o ecrã tem em mão.
   */
  setSimoDuplicates(executionId: string, counted: boolean): Promise<ValidationResult> {
    return firstValueFrom(
      this.http.put<ValidationResult>(`${this.base}/execucoes/${executionId}/duplicados-simo`, {
        counted,
      }),
    );
  }

  /** Os casos de períodos repetidos por tratar que têm créditos, com os pares sugeridos. */
  listReconciliationCandidates(executionId: string): Promise<ReconciliationCandidate[]> {
    return firstValueFrom(
      this.http.get<ReconciliationCandidate[]>(
        `${this.base}/execucoes/${executionId}/conciliacoes`,
      ),
    );
  }

  /** Concilia vários casos de uma vez — o servidor aceita todos ou nenhum. */
  reconcileCases(executionId: string, items: readonly CaseMatches[]): Promise<ReconciliationBatch> {
    return firstValueFrom(
      this.http.put<ReconciliationBatch>(`${this.base}/execucoes/${executionId}/conciliacoes`, {
        items,
      }),
    );
  }

  getSettings(): Promise<SlaSettings> {
    return firstValueFrom(this.http.get<SlaSettings>(`${this.base}/definicoes`));
  }

  /** O documento inteiro: o «aviso antes do prazo» não se valida a meio. */
  saveSettings(settings: { caseSlaDays: number; caseWarningDays: number }): Promise<SlaSettings> {
    return firstValueFrom(this.http.put<SlaSettings>(`${this.base}/definicoes`, settings));
  }

  async downloadReport(executionId: string, reportName: string): Promise<void> {
    const blob = await firstValueFrom(
      this.http.get(`${this.base}/execucoes/${executionId}/relatorio`, {
        responseType: 'blob',
      }),
    );

    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${reportName}.xlsx`;
    link.click();
    URL.revokeObjectURL(url);
  }
}

/**
 * O `validation` viaja como lista separada por vírgulas.
 *
 * `null` = sem filtro, e o parâmetro nem chega a ir na query. A selecção vazia
 * manda um token que não é classe nenhuma: o servidor ignora tokens
 * desconhecidos e não devolve linha nenhuma — que é precisamente o pedido.
 */
function serializeValidations(validations: Validation[] | null | undefined): string | null {
  if (!validations) return null;
  return validations.length > 0 ? validations.join(',') : 'nenhuma';
}
