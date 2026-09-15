/**
 * A forma de um e-Ticket — espelha o `domain/e_ticket.py` do serviço, como o
 * `sla.ts` espelha o `sla.py`.
 *
 * **Quem protege é o servidor.** Isto só serve para o operador saber o que está
 * mal enquanto escreve, em vez de carregar em «Guardar» e receber a recusa. As
 * regras têm de ser as mesmas dos dois lados; se mudarem, mudam lá primeiro.
 */

export const MAX_E_TICKET_LENGTH = 40;

/** Letra ou algarismo à cabeça (fecha a porta a fórmulas no Excel), depois só - _ / . */
const E_TICKET = /^[A-Za-z0-9][A-Za-z0-9._/-]*$/;

/** O que está mal no e-Ticket escrito, ou `null` se serve. Vazio serve: apaga. */
export function eTicketProblem(raw: string): string | null {
  const value = raw.trim();
  if (!value) return null;
  if (value.length > MAX_E_TICKET_LENGTH) {
    return `No máximo ${MAX_E_TICKET_LENGTH} caracteres.`;
  }
  if (!E_TICKET.test(value)) {
    return 'Só letras, algarismos e - _ / . — a começar por letra ou algarismo.';
  }
  return null;
}
