import {
  type ApplicationConfig,
  inject,
  type EnvironmentProviders,
  provideAppInitializer,
  provideBrowserGlobalErrorListeners,
  provideZonelessChangeDetection,
} from '@angular/core';
import { provideHttpClient, withFetch, withInterceptors } from '@angular/common/http';
import { provideRouter, withComponentInputBinding, withInMemoryScrolling } from '@angular/router';
import {
  AutoRefreshTokenService,
  createInterceptorCondition,
  INCLUDE_BEARER_TOKEN_INTERCEPTOR_CONFIG,
  includeBearerTokenInterceptor,
  type IncludeBearerTokenCondition,
  provideKeycloak,
  UserActivityService,
  withAutoRefreshToken,
} from 'keycloak-angular';

import { environment } from '../environments/environment';
import { routes } from './app.routes';
import { SessionStore } from './core/auth/session.store';
import { errorInterceptor } from './core/http/error.interceptor';

/** O bearer só vai para `/api/**` — sem isto, o token viajaria para qualquer domínio de terceiros. */
const apiOnly = createInterceptorCondition<IncludeBearerTokenCondition>({
  urlPattern: /^(https?:\/\/[^/]+)?\/api\//i,
  bearerPrefix: 'Bearer',
});

/**
 * Numa função para, com `authDisabled`, nada disto entrar no injector — não basta
 * ignorar o resultado: `provideKeycloak` inicializa e redirecciona ao SSO de qualquer forma.
 */
function keycloakProviders(): EnvironmentProviders[] {
  return [
    provideKeycloak({
      config: {
        url: environment.keycloakUrl,
        realm: environment.keycloakRealm,
        clientId: environment.keycloakClientId,
      },
      initOptions: {
        // Não há área pública: redirecciona já, em vez de piscar um ecrã vazio.
        onLoad: 'login-required',
        pkceMethod: 'S256',
        // Bloqueado por browsers que recusam cookies de terceiros; o refresh por actividade cobre.
        checkLoginIframe: false,
      },
      features: [
        withAutoRefreshToken({
          // Tem de bater certo com o `ssoSessionIdleTimeout` do realm.
          sessionTimeout: 30 * 60_000,
          onInactivityTimeout: 'logout',
        }),
      ],
      providers: [
        AutoRefreshTokenService,
        UserActivityService,
        { provide: INCLUDE_BEARER_TOKEN_INTERCEPTOR_CONFIG, useValue: [apiOnly] },
      ],
    }),
  ];
}

/** Sem Keycloak, `includeBearerTokenInterceptor` não tem config registada — sai da lista, não corre a seco. */
function interceptors() {
  return environment.authDisabled
    ? [errorInterceptor]
    : // A ordem importa: primeiro anexa o token, depois traduz o erro.
      [includeBearerTokenInterceptor, errorInterceptor];
}

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideZonelessChangeDetection(),

    ...(environment.authDisabled ? [] : keycloakProviders()),

    // Enche a sessão a partir do token já validado, para os componentes lerem signals.
    provideAppInitializer(() => {
      inject(SessionStore).refreshFromToken();
    }),

    provideHttpClient(withFetch(), withInterceptors(interceptors())),

    provideRouter(
      routes,
      withComponentInputBinding(),
      withInMemoryScrolling({ scrollPositionRestoration: 'top', anchorScrolling: 'enabled' }),
    ),
  ],
};
