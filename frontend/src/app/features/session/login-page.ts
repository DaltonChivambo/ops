import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { LucideLifeBuoy, LucideLoaderCircle, LucideLock, LucideUser } from '@lucide/angular';

import { SessionStore } from '../../core/auth/session.store';
import { ApiError } from '../../core/http/api-error';
import { CardComponent } from '../../shared/ui/card';

/**
 * Entrada na aplicação, com as credenciais do banco.
 *
 * Vive **fora** do `ShellComponent`: a barra lateral e o menu de utilizador
 * pressupõem sessão, e não há nada de útil a mostrar à volta de quem ainda não
 * entrou.
 *
 * As credenciais são as do GEEA — as mesmas do Windows. Por isso o formulário
 * não guarda nada, nem oferece «lembrar-me»: o que ficaria guardado era a
 * senha do domínio.
 */
@Component({
  selector: 'app-login-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    ReactiveFormsModule,
    CardComponent,
    LucideUser,
    LucideLock,
    LucideLoaderCircle,
    LucideLifeBuoy,
  ],
  template: `
    <div
      class="grid min-h-dvh place-items-center bg-gradient-to-br from-moza-50 via-white to-moza-100 p-6"
    >
      <div class="flex w-full max-w-md flex-col items-center">
        <section appCard class="w-full p-8 shadow-lg sm:p-10">
          <div class="text-center">
            <img src="mozaops_logo_sem_fundo.svg" alt="MozaOps" class="mx-auto h-8 w-auto" />
          </div>

          <form class="mt-8 flex flex-col gap-4" [formGroup]="form" (ngSubmit)="submit()">
            <label class="flex flex-col gap-1.5">
              <span class="text-xs font-medium text-moza-600">Utilizador</span>
              <div class="relative">
                <svg
                  lucideUser
                  [size]="16"
                  [strokeWidth]="1.8"
                  class="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-moza-300"
                ></svg>
                <input
                  formControlName="username"
                  autocomplete="username"
                  autocapitalize="none"
                  spellcheck="false"
                  class="w-full rounded-lg border border-gray-200 py-2 pr-3 pl-9 text-sm text-moza-800 outline-none transition-colors focus:border-moza-400 focus:ring-4 focus:ring-moza-100"
                />
              </div>
            </label>

            <label class="flex flex-col gap-1.5">
              <span class="text-xs font-medium text-moza-600">Password</span>
              <div class="relative">
                <svg
                  lucideLock
                  [size]="16"
                  [strokeWidth]="1.8"
                  class="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-moza-300"
                ></svg>
                <input
                  type="password"
                  formControlName="password"
                  autocomplete="current-password"
                  class="w-full rounded-lg border border-gray-200 py-2 pr-3 pl-9 text-sm text-moza-800 outline-none transition-colors focus:border-moza-400 focus:ring-4 focus:ring-moza-100"
                />
              </div>
            </label>

            @if (error()) {
              <p role="alert" class="rounded-lg bg-alert-50 px-3 py-2 text-sm text-alert-700">
                {{ error() }}
              </p>
            }

            <button
              type="submit"
              [disabled]="form.invalid || signingIn()"
              class="mt-1 flex items-center justify-center gap-2 rounded-lg bg-moza-700 px-3 py-2.5 text-sm font-medium text-white transition-colors hover:bg-moza-800 disabled:opacity-50 disabled:hover:bg-moza-700"
            >
              @if (signingIn()) {
                <svg lucideLoaderCircle [size]="16" [strokeWidth]="2" class="animate-spin"></svg>
              }
              {{ signingIn() ? 'A entrar…' : 'Entrar' }}
            </button>
          </form>

          <div class="mt-6 flex items-center justify-center gap-2 border-t border-gray-100 pt-5">
            <svg lucideLifeBuoy [size]="15" [strokeWidth]="1.9" class="shrink-0 text-moza-400"></svg>
            <a
              [href]="supportMailto"
              class="text-xs font-medium text-moza-500 hover:text-moza-700 hover:underline"
            >
              Precisa de assistência? Contacte o suporte técnico
            </a>
          </div>
        </section>

        <p class="mt-6 text-xs text-moza-400">Desenvolvido por DOP - Direção de Operações</p>
      </div>
    </div>
  `,
})
export class LoginPageComponent {
  private readonly session = inject(SessionStore);
  private readonly router = inject(Router);

  protected readonly form = inject(FormBuilder).nonNullable.group({
    username: ['', Validators.required],
    password: ['', Validators.required],
  });

  protected readonly signingIn = signal(false);
  protected readonly error = signal<string | null>(null);

  /** O assunto já vem preenchido — quem escreve não começa da folha em branco. */
  protected readonly supportMailto =
    'mailto:dalton.chivambo@mozabanco.co.mz?subject=' +
    encodeURIComponent('MozaOps — Pedido de suporte técnico');

  protected async submit(): Promise<void> {
    if (this.form.invalid || this.signingIn()) return;

    this.signingIn.set(true);
    this.error.set(null);

    const { username, password } = this.form.getRawValue();

    try {
      await this.session.signIn(username, password);
      // A password não fica no formulário depois de usada.
      this.form.reset();
      await this.router.navigateByUrl(this.destination());
    } catch (error) {
      // A mensagem do envelope já vem em português e escrita para o operador —
      // e é deliberadamente igual para utilizador errado e password errada.
      this.error.set(
        error instanceof ApiError
          ? error.message
          : 'Não foi possível entrar. Tente novamente.',
      );
    } finally {
      this.signingIn.set(false);
    }
  }

  /** Para onde a pessoa ia antes de a guarda a trazer para aqui. */
  private destination(): string {
    const returnUrl = new URLSearchParams(window.location.search).get('returnUrl');
    // Só caminhos desta aplicação: um `returnUrl` com URL absoluto seria um
    // reencaminhamento aberto, e um convite a phishing a partir de um link nosso.
    return returnUrl?.startsWith('/') && !returnUrl.startsWith('//') ? returnUrl : '/';
  }
}
