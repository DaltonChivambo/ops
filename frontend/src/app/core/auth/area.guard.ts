import { inject } from '@angular/core';
import { type CanActivateFn, Router } from '@angular/router';

import { findModule } from '../navigation';
import { SessionStore } from './session.store';

/**
 * Guarda de rota por área.
 *
 * Lê da sessão e não do token: as áreas do MozaOps são decididas pelo backend
 * (ver `session.store.ts`), e o token do GEEA não as traz.
 *
 * A área sai do próprio módulo que se está a abrir — não é preciso repeti-la
 * em cada rota, e uma automação nova fica protegida por estar no catálogo.
 * Módulos sem área (o Dashboard) são transversais: basta ter sessão.
 *
 * As duas saídas são diferentes de propósito. Sem sessão manda-se para o
 * login; com sessão e sem a área manda-se ao ecrã de «sem acesso», porque
 * repetir o login não mudava nada — a pessoa voltaria com as mesmas áreas.
 */
export const canOpenModule: CanActivateFn = (route, state) => {
  const session = inject(SessionStore);
  const router = inject(Router);

  if (!session.isAuthenticated()) {
    // O destino vai atrás para o login o devolver onde a pessoa ia.
    return router.createUrlTree(['/login'], { queryParams: { returnUrl: state.url } });
  }

  const area = findModule(route.paramMap.get('moduleId') ?? '')?.area ?? null;

  return area === null || session.hasArea(area) || router.createUrlTree(['/forbidden']);
};
