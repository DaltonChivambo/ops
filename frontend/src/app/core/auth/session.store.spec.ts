import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { IdentityApi, type PrincipalDto, type SessionDto } from './identity-api.service';
import { SessionStore } from './session.store';
import { TokenStore } from './token.store';

const PRINCIPAL: PrincipalDto = {
  subject: '6961d9f6-5529-457b-93cb-db82230a00cb',
  username: 'm001926',
  name: 'Dalton Chivambo',
  email: 'dalton.chivambo@mozabanco.co.mz',
  areas: ['channels'],
  departmentCode: '3230',
  department: 'Canais e Serviços de Integração',
  function: 'Director',
};

function session(overrides: Partial<PrincipalDto> = {}, token = 'token-1'): SessionDto {
  return { accessToken: token, expiresIn: 18000, principal: { ...PRINCIPAL, ...overrides } };
}

class FakeIdentityApi {
  loginResult: SessionDto | Error = session();
  refreshResult: SessionDto | Error = session();
  refreshes = 0;
  logouts = 0;

  async login(): Promise<SessionDto> {
    return unwrap(this.loginResult);
  }

  async refresh(): Promise<SessionDto> {
    this.refreshes += 1;
    return unwrap(this.refreshResult);
  }

  async logout(): Promise<void> {
    this.logouts += 1;
  }
}

function unwrap(value: SessionDto | Error): SessionDto {
  if (value instanceof Error) throw value;
  return value;
}

describe('SessionStore', () => {
  let api: FakeIdentityApi;
  let store: SessionStore;
  let tokens: TokenStore;

  beforeEach(() => {
    api = new FakeIdentityApi();
    TestBed.configureTestingModule({
      providers: [provideRouter([{ path: 'login', children: [] }]), { provide: IdentityApi, useValue: api }],
    });
    store = TestBed.inject(SessionStore);
    tokens = TestBed.inject(TokenStore);
  });

  it('começa sem sessão', () => {
    expect(store.isAuthenticated()).toBe(false);
    expect(store.areas()).toEqual([]);
  });

  it('guarda quem entrou, com a unidade orgânica', async () => {
    await store.signIn('m001926', 'senha');

    expect(store.isAuthenticated()).toBe(true);
    expect(store.principal()?.username).toBe('m001926');
    expect(store.principal()?.department).toBe('Canais e Serviços de Integração');
    expect(tokens.accessToken()).toBe('token-1');
  });

  it('recupera a sessão do cookie no arranque', async () => {
    await store.restore();

    expect(store.isAuthenticated()).toBe(true);
    expect(api.refreshes).toBe(1);
  });

  it('não rebenta no arranque quando não há sessão', async () => {
    api.refreshResult = new Error('401');

    await store.restore();

    expect(store.isAuthenticated()).toBe(false);
  });

  describe('áreas', () => {
    it('abre a área que o backend concedeu', async () => {
      await store.signIn('m001926', 'senha');

      expect(store.hasArea('channels')).toBe(true);
      expect(store.hasArea('customers-and-accounts')).toBe(false);
    });

    it('a função não muda nada', async () => {
      // Director e técnico da mesma unidade vêem o mesmo.
      api.loginResult = session({ function: 'Técnico' });
      await store.signIn('m007000', 'senha');

      expect(store.hasArea('channels')).toBe(true);
    });

    it('guarda áreas que o catálogo ainda não conhece', async () => {
      // Abrir uma área na configuração do backend não devia esperar por um SPA
      // publicado de novo. Sem módulo, não abre nada — mas o valor não se perde.
      api.loginResult = session({ areas: ['channels', 'ainda-nao-existe'] });
      await store.signIn('m001926', 'senha');

      expect(store.areas()).toEqual(['channels', 'ainda-nao-existe']);
    });

    it('sem áreas, não abre nenhuma — defesa, já que o backend nunca chega a devolver isto', async () => {
      api.loginResult = session({ areas: [] });
      await store.signIn('m009999', 'senha');

      expect(store.hasArea('channels')).toBe(false);
    });
  });

  describe('renovação', () => {
    it('devolve o token novo', async () => {
      api.refreshResult = session({}, 'token-2');

      await expect(store.renew()).resolves.toBe('token-2');
      expect(tokens.accessToken()).toBe('token-2');
    });

    it('N pedidos a falhar ao mesmo tempo fazem UMA renovação', async () => {
      await Promise.all([store.renew(), store.renew(), store.renew()]);

      expect(api.refreshes).toBe(1);
    });

    it('quando a sessão acabou mesmo, limpa tudo', async () => {
      await store.signIn('m001926', 'senha');
      api.refreshResult = new Error('401');

      await expect(store.renew()).resolves.toBeNull();
      expect(store.isAuthenticated()).toBe(false);
      expect(tokens.accessToken()).toBeNull();
    });
  });

  describe('sair', () => {
    it('limpa a sessão', async () => {
      await store.signIn('m001926', 'senha');
      await store.logout();

      expect(api.logouts).toBe(1);
      expect(store.isAuthenticated()).toBe(false);
      expect(tokens.accessToken()).toBeNull();
    });

    it('limpa mesmo que o servidor falhe', async () => {
      // Deixar o token ficar seria manter aberta uma porta que o operador
      // julga fechada.
      await store.signIn('m001926', 'senha');
      api.logout = () => Promise.reject(new Error('503'));

      await expect(store.logout()).rejects.toBeTruthy();
      expect(store.isAuthenticated()).toBe(false);
      expect(tokens.accessToken()).toBeNull();
    });
  });

  it('iniciais para o avatar', async () => {
    api.loginResult = session({ name: 'Ana Sousa' });
    await store.signIn('asousa', 'senha');

    expect(store.initials()).toBe('AS');
  });
});
