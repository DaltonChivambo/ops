import { HttpErrorResponse, type HttpInterceptorFn } from '@angular/common/http';
import { catchError, throwError } from 'rxjs';

import { ApiError, isErrorEnvelope } from './api-error';

/**
 * Traduz o envelope `{"error":{"code","message"}}` num `ApiError`.
 *
 * Os componentes passam a apanhar sempre a mesma coisa e a mostrar `err.message`
 * sem pensar — a mensagem já vem em português e escrita para o operador. Só
 * quando o servidor não responde é que a mensagem é nossa.
 */
export const errorInterceptor: HttpInterceptorFn = (request, next) =>
  next(request).pipe(
    catchError((response: unknown) => {
      if (!(response instanceof HttpErrorResponse)) {
        return throwError(() => response);
      }

      if (isErrorEnvelope(response.error)) {
        const { code, message } = response.error.error;
        return throwError(() => new ApiError(message, code, response.status));
      }

      // status 0 = não houve resposta: DNS, rede, serviço em baixo, CORS.
      if (response.status === 0) {
        return throwError(
          () =>
            new ApiError(
              'Não foi possível contactar o servidor. Verifique a ligação e tente de novo.',
              'network_error',
              0,
            ),
        );
      }

      // Um erro sem envelope significa que não veio do nosso código — um 502 do
      // Traefik, por exemplo. Não inventar uma mensagem que finja o contrário.
      return throwError(
        () =>
          new ApiError(
            'Ocorreu um erro inesperado. Se persistir, contacte o suporte.',
            'unexpected_error',
            response.status,
          ),
      );
    }),
  );
