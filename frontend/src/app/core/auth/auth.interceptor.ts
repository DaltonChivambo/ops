import type { HttpInterceptorFn, HttpRequest } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, from, switchMap, throwError } from 'rxjs';

import { environment } from '../../../environments/environment';
import { ApiError } from '../http/api-error';
import { SessionStore } from './session.store';
import { TokenStore } from './token.store';

/** Só `/api/**`. Sem isto, o token viajaria para qualquer domínio de terceiros. */
const API = /^(https?:\/\/[^/]+)?\/api\//i;

/**
 * Anexa o token aos pedidos à API e, num 401, renova **uma vez** e repete.
 *
 * O token de acesso dura menos do que a sessão. Sem esta renovação, o operador
 * era mandado para o ecrã de login a meio do trabalho por o token ter
 * expirado — com a sessão ainda válida no cookie.
 *
 * Corre por fora do `errorInterceptor`, por isso o que aqui chega já é um
 * `ApiError` e não a resposta em bruto.
 */
export const authInterceptor: HttpInterceptorFn = (request, next) => {
  const tokens = inject(TokenStore);
  const session = inject(SessionStore);

  // As rotas de sessão ficam de fora: o login não tem token para levar, e
  // deixar a renovação passar por aqui daria uma recursão sem fim.
  if (!API.test(request.url) || isSessionRoute(request.url)) {
    return next(request);
  }

  const send = (token: string | null) =>
    next(token ? withBearer(request, token) : request);

  return send(tokens.accessToken()).pipe(
    catchError((error: unknown) => {
      if (!(error instanceof ApiError) || !error.isUnauthenticated) {
        return throwError(() => error);
      }

      return from(session.renew()).pipe(
        switchMap((token) => (token ? send(token) : throwError(() => error))),
      );
    }),
  );
};

function withBearer(request: HttpRequest<unknown>, token: string): HttpRequest<unknown> {
  return request.clone({ setHeaders: { Authorization: `Bearer ${token}` } });
}

function isSessionRoute(url: string): boolean {
  return url.includes(`${environment.identityApiBase}/sessions`);
}
