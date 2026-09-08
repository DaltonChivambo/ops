import { computed, inject, Injectable, signal } from '@angular/core';

import { environment } from '../../../environments/environment';
import { DEV_PRINCIPAL } from './dev-session';
import { IdentityApi, type PrincipalDto } from './identity-api.service';
import { TokenStore } from './token.store';

/**
 * O que a aplicação sabe sobre quem está autenticado.
 *
 * Vem do `GET /api/identity/me`, e **não do token**: as áreas do MozaOps não
 * estão lá dentro. O GEEA traz os papéis do sistema dele (`work_queue`,
 * `manage_employee`) e a unidade orgânica; quem decide que áreas isso abre é o
 * backend, por configuração. Interpretar isso aqui obrigaria a publicar o SPA
 * de cada vez que alguém mudasse de unidade.
 *
 * Não há papéis. Dentro da área, quem opera, quem supervisiona e quem chefia
 * fazem hoje o mesmo.
 */
export interface Principal {
  readonly sub: string;
  readonly username: string;
  readonly name: string;
  readonly email: string;
  /** As áreas do catálogo (`navigation.ts`) que esta pessoa pode abrir. */
  readonly areas: readonly string[];
  readonly departmentCode: string;
  readonly department: string;
  /** O nome da claim é do GEEA: a função da pessoa, não uma função de código. */
  readonly function: string;
}

/** A sessão, em signals. Sem tabela local de utilizadores. */
@Injectable({ providedIn: 'root' })
export class SessionStore {
  private readonly api = inject(IdentityApi);
  private readonly tokens = inject(TokenStore);

  private readonly principalSignal = signal<Principal | null>(null);

  /** Renovação a decorrer. Partilhada, para N pedidos a falhar ao mesmo tempo
      não dispararem N renovações — e N logins depois delas. */
  private renewal: Promise<string | null> | null = null;

  readonly principal = this.principalSignal.asReadonly();
  readonly isAuthenticated = computed(() => this.principalSignal() !== null);
  readonly areas = computed<readonly string[]>(() => this.principalSignal()?.areas ?? []);

  /** Entrou, mas não é de área nenhuma: vê o Dashboard e mais nada. */
  readonly hasNoArea = computed(() => this.isAuthenticated() && this.areas().length === 0);

  /** Iniciais para o avatar: «Ana Sousa» → «AS». */
  readonly initials = computed(() => {
    const name = this.principalSignal()?.name?.trim();
    if (!name) return '?';
    const parts = name.split(/\s+/);
    const first = parts.at(0)?.[0] ?? '';
    const last = parts.length > 1 ? (parts.at(-1)?.[0] ?? '') : '';
    return (first + last).toUpperCase();
  });

  /**
   * Chamado uma vez, no arranque: tenta recuperar a sessão do cookie.
   *
   * Falhar aqui é o caso normal de quem ainda não entrou — não é erro, e por
   * isso não se propaga. Quem decide o que fazer a seguir é a guarda de rota.
   */
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

  /**
   * Renova o token de acesso. Devolve `null` se a sessão acabou mesmo.
   *
   * Usado pelo interceptor quando um pedido leva 401 — o token de acesso dura
   * menos do que a sessão, e expirar não devia mandar ninguém para o ecrã de
   * login a meio do trabalho.
   */
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

  /** Protege a interface, não a verdade — a verdade é a guarda do servidor. */
  hasArea(area: string): boolean {
    return this.areas().includes(area);
  }

  async logout(): Promise<void> {
    if (environment.authDisabled) {
      // Sem sessão a sério não há nada que terminar; recarregar devolve a de dev.
      window.location.reload();
      return;
    }

    try {
      await this.api.logout();
    } finally {
      // Mesmo que o pedido falhe, deste lado a sessão acabou: deixar o token
      // ficar seria manter aberta uma porta que o operador julga fechada.
      this.clear();
    }
  }

  private accept(token: string, principal: PrincipalDto): void {
    this.tokens.set(token);
    this.principalSignal.set({
      sub: principal.subject,
      username: principal.username,
      name: principal.name || principal.username,
      email: principal.email,
      // Sem filtro por ids conhecidos: uma área acrescentada na configuração
      // do backend não devia depender de um SPA publicado de novo para valer.
      // O que o SPA não conhece não abre nada, porque não há módulo para abrir.
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
