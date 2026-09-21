import { computed, inject, Injectable, signal } from '@angular/core';
import { Router } from '@angular/router';

import { environment } from '../../../environments/environment';
import { ALL_AREAS } from '../navigation';
import { DEV_PRINCIPAL } from './dev-session';
import { AuthApi, type PrincipalDto } from './auth-api.service';
import { TokenStore } from './token.store';

/**
 * Vem do `GET /api/auth-service/me`, e não do token: o SPA guarda o token mas não
 * o abre, e as áreas são o que o backend junta dos papéis do realm com a
 * configuração. Lê-las aqui obrigaria a publicar o SPA a cada mudança de
 * acesso.
 */
export interface Principal {
  readonly sub: string;
  readonly username: string;
  readonly name: string;
  readonly email: string;
  /** Áreas do catálogo em `navigation.ts`. */
  readonly areas: readonly string[];
  readonly departmentCode: string;
  readonly department: string;
  /** Claim do GEEA: a função da pessoa, não uma função de código. */
  readonly function: string;
}

@Injectable({ providedIn: 'root' })
export class SessionStore {
  private readonly api = inject(AuthApi);
  private readonly tokens = inject(TokenStore);
  private readonly router = inject(Router);

  private readonly principalSignal = signal<Principal | null>(null);

  /** Partilhada: N pedidos a levar 401 ao mesmo tempo não podem disparar N renovações. */
  private renewal: Promise<string | null> | null = null;

  readonly principal = this.principalSignal.asReadonly();
  readonly isAuthenticated = computed(() => this.principalSignal() !== null);
  readonly areas = computed<readonly string[]>(() => this.principalSignal()?.areas ?? []);

  /** «Ana Sousa» → «AS». */
  readonly initials = computed(() => {
    const name = this.principalSignal()?.name?.trim();
    if (!name) return '?';
    const parts = name.split(/\s+/);
    const first = parts.at(0)?.[0] ?? '';
    const last = parts.length > 1 ? (parts.at(-1)?.[0] ?? '') : '';
    return (first + last).toUpperCase();
  });

  /** Falhar é o caso normal de quem ainda não entrou, por isso não se propaga. */
  async restore(): Promise<void> {
    if (environment.authDisabled) {
      this.principalSignal.set(DEV_PRINCIPAL);
      return;
    }

    try {
      const session = await this.api.refresh();
      this.accept(session.accessToken, session.principal);
    } catch {
      this.clear();
    }
  }

  async signIn(username: string, password: string): Promise<void> {
    const session = await this.api.login(username, password);
    this.accept(session.accessToken, session.principal);
  }

  /** `null` quando a sessão acabou mesmo. */
  renew(): Promise<string | null> {
    if (environment.authDisabled) return Promise.resolve(null);

    this.renewal ??= this.api
      .refresh()
      .then((session) => {
        this.accept(session.accessToken, session.principal);
        return session.accessToken;
      })
      .catch(() => {
        this.clear();
        return null;
      })
      .finally(() => {
        this.renewal = null;
      });

    return this.renewal;
  }

  /**
   * Protege a interface, não a verdade — a verdade é a guarda do servidor, que
   * decide isto da mesma maneira (`Principal.has_area`).
   */
  hasArea(area: string): boolean {
    const areas = this.areas();
    return areas.includes(ALL_AREAS) || areas.includes(area);
  }

  async logout(): Promise<void> {
    if (environment.authDisabled) {
      window.location.reload();
      return;
    }

    try {
      await this.api.logout();
    } finally {
      // Mesmo que o pedido falhe, deste lado a sessão acabou.
      this.clear();
      await this.router.navigateByUrl('/login');
    }
  }

  private accept(token: string, principal: PrincipalDto): void {
    this.tokens.set(token);
    this.principalSignal.set({
      sub: principal.subject,
      username: principal.username,
      name: principal.name || principal.username,
      email: principal.email,
      areas: principal.areas,
      departmentCode: principal.departmentCode,
      department: principal.department,
      function: principal.function,
    });
  }

  private clear(): void {
    this.tokens.clear();
    this.principalSignal.set(null);
  }
}
