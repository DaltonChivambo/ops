import { inject } from '@angular/core';
import { type CanActivateFn, Router } from '@angular/router';

import type { Role } from './roles';
import { SessionStore } from './session.store';

/**
 * Guarda de rota por papel.
 *
 * Lê da sessão e não do token: os papéis do MozaOps são decididos pelo backend
 * (ver `session.store.ts`), e o token do GEEA não os traz.
 *
 * As duas saídas são diferentes de propósito. Sem sessão manda-se entrar; com
 * sessão e sem papel manda-se ao ecrã de «sem permissão», porque repetir o
 * login não mudava nada — a pessoa voltaria com os mesmos papéis.
 */
export const canAccess = (...allowed: readonly Role[]): CanActivateFn => {
  return (_route, state) => {
    const session = inject(SessionStore);
    const router = inject(Router);

    if (!session.isAuthenticated()) {
      // O destino vai atrás para o login o devolver onde a pessoa ia.
      return router.createUrlTree(['/entrar'], {
        queryParams: { regressar: state.url },
      });
    }

    return session.hasAny(allowed) || router.createUrlTree(['/sem-permissao']);
  };
};
