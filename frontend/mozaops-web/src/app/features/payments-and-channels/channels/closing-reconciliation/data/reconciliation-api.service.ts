import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { ApiError } from '../../../../../core/http/api-error';
import { environment } from '../../../../../../environments/environment';
import type {
  CaseStatus,
  ClosingSummary,
  DetailsPage,
  DetailsQuery,
  ExecutionOutcome,
  KeyBreakdown,
  PendingCase,
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
  counts: { all: 0, match: 0, mismatch: 0, missing: 0, zero: 0, duplicated: 0 },
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
    return firstValueFrom(
      this.http.get<ValidationResult | null>(`${this.base}/execucoes/ultima`),
    );
  }

  async listDetails(executionId: string, query: DetailsQuery = {}): Promise<DetailsPage> {
    let params = new HttpParams();
    if (query.page !== undefined) params = params.set('page', query.page);
    if (query.perPage !== undefined) params = params.set('perPage', query.perPage);
    if (query.q) params = params.set('q', query.q);

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
