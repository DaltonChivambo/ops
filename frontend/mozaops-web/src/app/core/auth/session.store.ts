import { computed, inject, Injectable, signal } from '@angular/core';
import Keycloak from 'keycloak-js';

import { environment } from '../../../environments/environment';
import { DEV_PRINCIPAL } from './dev-session';
import { RESOLVERS, ROLES, type Role, WRITERS } from './roles';

/** O que a aplicação sabe sobre quem está autenticado. Vem todo do token. */
export interface Principal {
  readonly sub: string;
  readonly username: string;
  readonly name: string;
  readonly email: string;
  readonly roles: readonly Role[];
}

/** A sessão, em signals — vem toda do access token do Keycloak, sem tabela local de utilizadores. */
@Injectable({ providedIn: 'root' })
export class SessionStore {
  /** `optional`: com `authDisabled` o `provideKeycloak` não entra nos providers. */
  private readonly keycloak = inject(Keycloak, { optional: true });

  private readonly principalSignal = signal<Principal | null>(null);

  readonly principal = this.principalSignal.asReadonly();
  readonly isAuthenticated = computed(() => this.principalSignal() !== null);
  readonly roles = computed<readonly Role[]>(() => this.principalSignal()?.roles ?? []);

  /** Pode correr automações e editar casos — protege a interface, não a verdade (isso é o servidor). */
  readonly canExecute = computed(() => this.hasAny(WRITERS));

  /** Pode marcar um caso como regularizado. */
  readonly canResolve = computed(() => this.hasAny(RESOLVERS));

  /** Iniciais para o avatar: «Ana Sousa» → «AS». */
  readonly initials = computed(() => {
    const name = this.principalSignal()?.name?.trim();
    if (!name) return '?';
    const parts = name.split(/\s+/);
    const first = parts.at(0)?.[0] ?? '';
    const last = parts.length > 1 ? (parts.at(-1)?.[0] ?? '') : '';
    return (first + last).toUpperCase();
  });

  /** Chamado uma vez, no arranque, depois de o Keycloak inicializar. */
  refreshFromToken(): void {
    if (environment.authDisabled) {
      this.principalSignal.set(DEV_PRINCIPAL);
      return;
    }

    const claims = this.keycloak?.tokenParsed as KeycloakClaims | undefined;
    if (!claims?.sub) {
      this.principalSignal.set(null);
      return;
    }

    this.principalSignal.set({
      sub: claims.sub,
      username: claims.preferred_username ?? '',
      name: claims.name ?? claims.preferred_username ?? '',
      email: claims.email ?? '',
      // Filtra: o realm traz também papéis técnicos do Keycloak que não nos dizem nada.
      roles: (claims.realm_access?.roles ?? []).filter(isKnownRole),
    });
  }

  hasAny(allowed: readonly Role[]): boolean {
    const mine = this.roles();
    return allowed.some((role) => mine.includes(role));
  }

  logout(): Promise<void> {
    this.principalSignal.set(null);

    // Sem Keycloak não há sessão a terminar — recarregar devolve a sessão de dev.
    if (!this.keycloak) {
      window.location.reload();
      return Promise.resolve();
    }

    return this.keycloak.logout({ redirectUri: window.location.origin });
  }
}

interface KeycloakClaims {
  sub?: string;
  preferred_username?: string;
  name?: string;
  email?: string;
  realm_access?: { roles?: string[] };
}

function isKnownRole(role: string): role is Role {
  return (ROLES as readonly string[]).includes(role);
}
