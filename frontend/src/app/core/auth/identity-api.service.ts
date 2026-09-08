import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { environment } from '../../../environments/environment';

/** O que o serviço `identity` devolve. `function` é o nome da claim no GEEA. */
export interface PrincipalDto {
  readonly subject: string;
  readonly username: string;
  readonly name: string;
  readonly email: string;
  readonly roles: readonly string[];
  readonly departmentCode: string;
  readonly department: string;
  readonly function: string;
}

export interface SessionDto {
  readonly accessToken: string;
  readonly expiresIn: number;
  readonly principal: PrincipalDto;
}

/**
 * O único sítio do SPA que fala com o serviço de sessões.
 *
 * As credenciais vão **no corpo de um POST** e não numa query string: o GEEA
 * obriga o nosso backend a pô-las num URL quando fala com ele, mas o que sai
 * do browser não tem de ficar no histórico nem nos logs de tudo o que houver
 * pelo caminho.
 *
 * `withCredentials` não é preciso: o SPA e a API partilham origem por desenho
 * (o Traefik à frente, o proxy do `ng serve` em dev), por isso o cookie de
 * renovação viaja sozinho.
 */
@Injectable({ providedIn: 'root' })
export class IdentityApi {
  private readonly http = inject(HttpClient);
  private readonly base = environment.identityApiBase;

  login(username: string, password: string): Promise<SessionDto> {
    return firstValueFrom(
      this.http.post<SessionDto>(`${this.base}/sessions`, { username, password }),
    );
  }

  /** Troca o cookie `HttpOnly` por um token de acesso novo. */
  refresh(): Promise<SessionDto> {
    return firstValueFrom(this.http.post<SessionDto>(`${this.base}/sessions/refresh`, {}));
  }

  logout(): Promise<void> {
    return firstValueFrom(this.http.delete<void>(`${this.base}/sessions`));
  }

  me(): Promise<PrincipalDto> {
    return firstValueFrom(this.http.get<PrincipalDto>(`${this.base}/me`));
  }
}
