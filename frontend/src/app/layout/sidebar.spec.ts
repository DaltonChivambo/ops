import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { AuthApi, type SessionDto } from '../core/auth/auth-api.service';
import { SessionStore } from '../core/auth/session.store';
import { SidebarComponent } from './sidebar';

function session(areas: readonly string[]): SessionDto {
  return {
    accessToken: 'token',
    expiresIn: 18000,
    principal: {
      subject: 's',
      username: 'm002000',
      name: 'John Doe',
      email: 'john.doe@mozabanco.co.mz',
      areas,
      departmentCode: '3230',
      department: 'Canais e Serviços de Integração',
      function: 'Técnico',
    },
  };
}

/**
 * A navegação da barra, depois de entrar com estas áreas.
 *
 * Só o `<nav>`: o cabeçalho da barra tem o nome do Departamento («Meios de
 * Pagamentos e Canais») escrito por extenso, e apanhá-lo aqui dava por
 * visível um grupo que está escondido.
 */
async function sidebarNavFor(
  areas: readonly string[],
  options: { collapsed?: boolean } = {},
): Promise<HTMLElement> {
  // Reposto aqui, e não só no `afterEach`: há testes que montam a barra duas
  // vezes, com sessões diferentes.
  TestBed.resetTestingModule();
  TestBed.configureTestingModule({
    providers: [
      provideRouter([]),
      { provide: AuthApi, useValue: { login: () => Promise.resolve(session(areas)) } },
    ],
  });

  await TestBed.inject(SessionStore).signIn('m002000', 'senha');

  const fixture = TestBed.createComponent(SidebarComponent);
  fixture.componentRef.setInput('collapsed', options.collapsed ?? false);
  fixture.detectChanges();
  return fixture.nativeElement.querySelector('nav');
}

async function sidebarTextFor(areas: readonly string[]): Promise<string> {
  return (await sidebarNavFor(areas)).textContent ?? '';
}

/**
 * Os rótulos das linhas de primeiro nível.
 *
 * Pelo `aria-label`, que só os botões de primeiro nível têm: as opções de um
 * grupo continuam no DOM quando ele está fechado — o que as esconde é a
 * grelha a 0fr — e pelo texto entrariam na conta.
 */
function rowLabels(nav: HTMLElement): readonly string[] {
  return [...nav.querySelectorAll('button[aria-label]')].map(
    (button) => button.getAttribute('aria-label') ?? '',
  );
}

describe('SidebarComponent', () => {
  afterEach(() => TestBed.resetTestingModule());

  it('quem só é de Canais não vê as outras áreas', async () => {
    const text = await sidebarTextFor(['channels']);

    expect(text).toContain('Canais');
    expect(text).not.toContain('Pagamentos');
    expect(text).not.toContain('Fraudes');
  });

  it('o papel que abre tudo mostra tudo', async () => {
    const text = await sidebarTextFor(['all-areas']);

    expect(text).toContain('Canais');
    expect(text).toContain('Pagamentos');
    expect(text).toContain('Fraudes');
  });

  it('sem área nenhuma sobra o que é transversal', async () => {
    const text = await sidebarTextFor([]);

    expect(text).toContain('Dashboard');
    expect(text).not.toContain('Pagamentos');
  });

  it('encolhida, um grupo pequeno dá lugar às opções dele', async () => {
    const nav = await sidebarNavFor(['all-areas'], { collapsed: true });
    const labels = rowLabels(nav);

    // Canais tem três opções: sobem, e o grupo desaparece.
    expect(labels).toContain('POS');
    expect(labels).toContain('ATM');
    expect(labels).toContain('Quiosques');
    expect(labels).not.toContain('Canais');
  });

  it('encolhida, um grupo cujas opções ainda não têm página mantém-se', async () => {
    // «Cartões» e «Cheques» soltos seriam ícones que não fazem nada.
    const labels = rowLabels(await sidebarNavFor(['all-areas'], { collapsed: true }));

    expect(labels).toContain('Pagamentos');
    expect(labels).not.toContain('Cartões');
  });

  it('expandida, os grupos ficam como estavam', async () => {
    const labels = rowLabels(await sidebarNavFor(['all-areas']));

    expect(labels).toContain('Canais');
    expect(labels).toContain('Pagamentos');
    expect(labels).toContain('Fraudes');
  });
});
