import type { ClosingDetail, PendingCase } from './models';

/**
 * Um caso visto como fecho — o que o painel de detalhe precisa para abrir a chave.
 *
 * O painel parte de um fecho (dá-lhe a identidade e o cabeçalho) e vai buscar o
 * resto da chave ao servidor. Aberto a partir de um caso não há fecho clicado:
 * constrói-se um com o que o caso sabe, e o painel corrige o tipo de fecho assim
 * que os fechos verdadeiros chegam.
 */
export const caseToDetail = (item: PendingCase): ClosingDetail => ({
  id: item.id,
  posId: item.posId,
  merchant: item.merchant,
  accountNumber: item.accountNumber,
  period: item.period,
  key: item.key,
  simoClosingDate: '',
  operationNumber: 0,
  simoClosingTotal: item.simoAmount,
  simoKeyTotal: item.simoAmount,
  closingDescription: null,
  bankaCreditDate: null,
  bankaClosingTotal: item.bankaAmount,
  closingType: 'n.a',
  validation: item.type,
  difference: item.bankaAmount - item.simoAmount,
  simoClosingsCount: item.simoClosingsCount,
  bankaMovementsCount: item.bankaMovementsCount,
  simoDuplicate: false,
});
