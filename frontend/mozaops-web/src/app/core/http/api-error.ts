/**
 * O envelope de erro que todos os serviços devolvem.
 *
 * A `message` vem já em português e é para mostrar ao operador tal como está:
 * os erros de negócio são conteúdo, não diagnóstico. O `code` é para o código
 * decidir, nunca para o utilizador ler.
 */
export interface ErrorEnvelope {
  error: { code: string; message: string };
}

export class ApiError extends Error {
  constructor(
    override readonly message: string,
    readonly code: string,
    readonly status: number,
  ) {
    super(message);
    this.name = 'ApiError';
  }

  /** 401/403 têm tratamento próprio na interface: sessão contra permissão. */
  get isUnauthenticated(): boolean {
    return this.status === 401;
  }

  get isForbidden(): boolean {
    return this.status === 403;
  }

  /** 422 é a excepção de negócio — a mensagem é para mostrar em destaque. */
  get isBusinessRule(): boolean {
    return this.status === 422;
  }
}

export function isErrorEnvelope(value: unknown): value is ErrorEnvelope {
  if (typeof value !== 'object' || value === null) return false;
  const candidate = (value as ErrorEnvelope).error;
  return (
    typeof candidate === 'object' &&
    candidate !== null &&
    typeof candidate.code === 'string' &&
    typeof candidate.message === 'string'
  );
}
