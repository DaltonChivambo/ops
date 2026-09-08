import {
  type ApplicationConfig,
  inject,
  provideAppInitializer,
  provideBrowserGlobalErrorListeners,
  provideZonelessChangeDetection,
} from '@angular/core';
import { provideHttpClient, withFetch, withInterceptors } from '@angular/common/http';
import { provideRouter, withComponentInputBinding, withInMemoryScrolling } from '@angular/router';

import { routes } from './app.routes';
import { authInterceptor } from './core/auth/auth.interceptor';
import { SessionStore } from './core/auth/session.store';
import { errorInterceptor } from './core/http/error.interceptor';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideZonelessChangeDetection(),

    /**
     * Recupera a sessão antes de a primeira rota ser avaliada.
     *
     * O `return` não é decorativo: sem ele o Angular não espera, e a guarda de
     * rota corria com a sessão ainda por carregar — mandando para o ecrã de
     * login quem já tinha sessão válida no cookie.
     */
    provideAppInitializer(() => inject(SessionStore).restore()),

    // A ordem importa, e é o inverso da de leitura: o `authInterceptor` fica
    // por fora, por isso o erro que lhe chega já foi traduzido em `ApiError`
    // pelo de dentro — que é a forma que ele espera para decidir renovar.
    provideHttpClient(withFetch(), withInterceptors([authInterceptor, errorInterceptor])),

    provideRouter(
      routes,
      withComponentInputBinding(),
      withInMemoryScrolling({ scrollPositionRestoration: 'top', anchorScrolling: 'enabled' }),
    ),
  ],
};
