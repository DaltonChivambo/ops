import { Injectable, signal } from '@angular/core';

/**
 * O token de acesso, **só em memória**.
 *
 * Nunca `localStorage` nem `sessionStorage`: o que lá está é legível por
 * qualquer script que corra na página, e um XSS passaria a valer uma sessão
 * inteira em vez de um pedido. Em memória, o token morre com o separador.
 *
 * O preço é perdê-lo ao recarregar a página — e é isso que o cookie de
 * renovação resolve: `SessionStore.restore()` troca-o por um token novo no
 * arranque, sem a password voltar a ser pedida. Esse cookie é `HttpOnly`, por
 * isso nem este ficheiro lhe consegue tocar.
 */
@Injectable({ providedIn: 'root' })
export class TokenStore {
  private readonly token = signal<string | null>(null);

  readonly accessToken = this.token.asReadonly();

  set(value: string): void {
    this.token.set(value);
  }

  clear(): void {
    this.token.set(null);
  }
}
