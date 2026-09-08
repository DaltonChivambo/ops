import { Injector, runInInjectionContext } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import {
  type ActivatedRouteSnapshot,
  convertToParamMap,
  provideRouter,
  type RouterStateSnapshot,
  UrlTree,
} from '@angular/router';

import { canOpenModule } from './area.guard';
import { IdentityApi, type SessionDto } from './identity-api.service';
import { SessionStore } from './session.store';

function sessao(areas: readonly string[]): SessionDto {
  return {
    accessToken: 'token',
    expiresIn: 18000,
    principal: {
      subject: 's',
      username: 'm001926',
      name: 'Dalton Chivambo',
      email: 'd@mozabanco.co.mz',
      areas,
      departmentCode: '3230',
      department: 'Canais e Serviços de Integração',
      function: 'Director',
    },
  };
}

describe('canOpenModule', () => {
  let api: { login: () => Promise<SessionDto> };
  let injector: Injector;

  /** `pos` é da área «canais»; `dashboard` não é de nenhuma. */
  const abrir = (moduleId: string) =>
    runInInjectionContext(injector, () =>
      canOpenModule(
        { paramMap: convertToParamMap({ moduleId }) } as ActivatedRouteSnapshot,
        { url: `/${moduleId}` } as RouterStateSnapshot,
      ),
    );

  beforeEach(() => {
    api = { login: () => Promise.resolve(sessao(['canais'])) };
    TestBed.configureTestingModule({
      providers: [provideRouter([]), { provide: IdentityApi, useValue: api }],
    });
    injector = TestBed.inject(Injector);
  });

  it('sem sessão, manda entrar — e leva o destino atrás', () => {
    const resultado = abrir('pos');

    expect(resultado).toBeInstanceOf(UrlTree);
    expect(String(resultado)).toContain('/entrar');
    expect(String(resultado)).toContain('regressar');
  });

  it('com a área do módulo, deixa passar', async () => {
    await TestBed.inject(SessionStore).signIn('m001926', 'senha');

    expect(abrir('pos')).toBe(true);
  });

  it('sem a área do módulo, manda ao ecrã de sem acesso', async () => {
    // E não de volta ao login: repetir o login traria as mesmas áreas.
    api.login = () => Promise.resolve(sessao([]));
    await TestBed.inject(SessionStore).signIn('m009999', 'senha');

    const resultado = abrir('pos');

    expect(resultado).toBeInstanceOf(UrlTree);
    expect(String(resultado)).toContain('/sem-acesso');
    expect(String(resultado)).not.toContain('/entrar');
  });

  it('um módulo transversal abre-se sem área nenhuma', async () => {
    api.login = () => Promise.resolve(sessao([]));
    await TestBed.inject(SessionStore).signIn('m009999', 'senha');

    expect(abrir('dashboard')).toBe(true);
  });

  it('um módulo que não existe no catálogo trata-se como transversal', async () => {
    // Quem decide que a página não existe é o router, não a guarda: devolver
    // «sem acesso» a um URL inventado dizia à pessoa que o problema era dela.
    await TestBed.inject(SessionStore).signIn('m001926', 'senha');

    expect(abrir('nao-existe')).toBe(true);
  });
});
