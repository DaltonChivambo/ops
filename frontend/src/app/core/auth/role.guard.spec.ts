import { Injector, runInInjectionContext } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import {
  type ActivatedRouteSnapshot,
  provideRouter,
  type RouterStateSnapshot,
  UrlTree,
} from '@angular/router';

import { IdentityApi, type SessionDto } from './identity-api.service';
import { canAccess } from './role.guard';
import { READERS, RESOLVERS, type Role } from './roles';
import { SessionStore } from './session.store';

function sessao(roles: readonly string[]): SessionDto {
  return {
    accessToken: 'token',
    expiresIn: 18000,
    principal: {
      subject: 's',
      username: 'm001926',
      name: 'Dalton Chivambo',
      email: 'd@mozabanco.co.mz',
      roles,
      departmentCode: '2350',
      department: 'Departamento de Apoio Operacional',
      function: 'Director',
    },
  };
}

describe('canAccess', () => {
  let api: { login: () => Promise<SessionDto> };
  let injector: Injector;

  const correr = (...allowed: readonly Role[]) =>
    runInInjectionContext(injector, () =>
      canAccess(...allowed)(
        {} as ActivatedRouteSnapshot,
        { url: '/pos/validacao-credito-fecho' } as RouterStateSnapshot,
      ),
    );

  beforeEach(() => {
    api = { login: () => Promise.resolve(sessao(['operator'])) };
    TestBed.configureTestingModule({
      providers: [provideRouter([]), { provide: IdentityApi, useValue: api }],
    });
    injector = TestBed.inject(Injector);
  });

  it('sem sessão, manda entrar — e leva o destino atrás', () => {
    const resultado = correr(...READERS);

    expect(resultado).toBeInstanceOf(UrlTree);
    expect(String(resultado)).toContain('/entrar');
    expect(String(resultado)).toContain('regressar');
  });

  it('com o papel certo, deixa passar', async () => {
    await TestBed.inject(SessionStore).signIn('m001926', 'senha');

    expect(correr(...READERS)).toBe(true);
  });

  it('com sessão e sem o papel, manda ao ecrã de sem permissão', async () => {
    // E não de volta ao login: repetir o login traria os mesmos papéis.
    await TestBed.inject(SessionStore).signIn('m001926', 'senha');

    const resultado = correr(...RESOLVERS);

    expect(resultado).toBeInstanceOf(UrlTree);
    expect(String(resultado)).toContain('/sem-permissao');
    expect(String(resultado)).not.toContain('/entrar');
  });
});
