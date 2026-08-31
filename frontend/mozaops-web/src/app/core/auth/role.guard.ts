import { inject } from '@angular/core';
import { type CanActivateFn, Router } from '@angular/router';
import { createAuthGuard } from 'keycloak-angular';

import { environment } from '../../../environments/environment';
import type { Role } from './roles';
import { SessionStore } from './session.store';

/** Guarda de rota por papel — usa `keycloak-angular` em vez de interpretar `realm_access.roles` à mão. */
export const canAccess = (...allowed: readonly Role[]): CanActivateFn => {
  // Sem Keycloak lê-se da sessão de dev, a sério (não `true` a seco): trocar os
  // papéis em dev-session.ts continua a exercitar o guarda e o ecrã /sem-permissao.
  if (environment.authDisabled) {
    return () => {
      const session = inject(SessionStore);
      return session.hasAny(allowed) || inject(Router).createUrlTree(['/sem-permissao']);
    };
  }

  return createAuthGuard<CanActivateFn>(async (_route, _state, { authenticated, grantedRoles }) => {
    if (!authenticated) return false;

    const mine = grantedRoles.realmRoles ?? [];
    if (allowed.some((role) => mine.includes(role))) return true;

    // Sem o papel, não de login — mandá-lo de novo ao Keycloak dava um ciclo infinito.
    return inject(Router).createUrlTree(['/sem-permissao']);
  });
};
