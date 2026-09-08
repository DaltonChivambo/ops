import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';

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
 * As credenciais são as do GEEA — as mesmas do Windows. O ecrã diz isso, para
 * ninguém procurar uma password que não existe; e o formulário não guarda nada,
 * nem oferece «lembrar-me», porque o que ficaria guardado era a senha do
 * domínio.
 */
@Component({
  selector: 'app-login-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule, CardComponent],
  template: `
    <div class="grid min-h-dvh place-items-center bg-moza-50 p-6">
      <section appCard class="w-full max-w-sm">
        <h1 class="text-lg font-semibold text-moza-800">MozaOps</h1>
        <p class="mt-1 text-sm text-moza-500">
          Entre com as suas credenciais do banco — as mesmas do Windows.
        </p>

        <form class="mt-6 flex flex-col gap-4" [formGroup]="form" (ngSubmit)="submit()">
          <label class="flex flex-col gap-1.5">
            <span class="text-xs font-medium text-moza-600">Utilizador</span>
            <input
              formControlName="username"
              autocomplete="username"
              autocapitalize="none"
              spellcheck="false"
              class="rounded-lg border border-gray-200 px-3 py-2 text-sm text-moza-800 outline-none focus:border-moza-400"
            />
          </label>

          <label class="flex flex-col gap-1.5">
            <span class="text-xs font-medium text-moza-600">Password</span>
            <input
              type="password"
              formControlName="password"
              autocomplete="current-password"
              class="rounded-lg border border-gray-200 px-3 py-2 text-sm text-moza-800 outline-none focus:border-moza-400"
            />
          </label>

          @if (erro()) {
            <p role="alert" class="rounded-lg bg-alert-50 px-3 py-2 text-sm text-alert-700">
              {{ erro() }}
            </p>
          }

          <button
            type="submit"
            [disabled]="form.invalid || aEntrar()"
            class="rounded-lg bg-moza-700 px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {{ aEntrar() ? 'A entrar…' : 'Entrar' }}
          </button>
        </form>
      </section>
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

  protected readonly aEntrar = signal(false);
  protected readonly erro = signal<string | null>(null);

  protected async submit(): Promise<void> {
    if (this.form.invalid || this.aEntrar()) return;

    this.aEntrar.set(true);
    this.erro.set(null);

    const { username, password } = this.form.getRawValue();

    try {
      await this.session.signIn(username, password);
      // A password não fica no formulário depois de usada.
      this.form.reset();
      await this.router.navigateByUrl(this.destino());
    } catch (error) {
      // A mensagem do envelope já vem em português e escrita para o operador —
      // e é deliberadamente igual para utilizador errado e password errada.
      this.erro.set(
        error instanceof ApiError
          ? error.message
          : 'Não foi possível entrar. Tente novamente.',
      );
    } finally {
      this.aEntrar.set(false);
    }
  }

  /** Para onde a pessoa ia antes de a guarda a trazer para aqui. */
  private destino(): string {
    const regressar = new URLSearchParams(window.location.search).get('regressar');
    // Só caminhos desta aplicação: um `regressar` com URL absoluto seria um
    // reencaminhamento aberto, e um convite a phishing a partir de um link nosso.
    return regressar?.startsWith('/') && !regressar.startsWith('//') ? regressar : '/';
  }
}
