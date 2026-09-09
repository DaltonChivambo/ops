import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import {
  LucideEye,
  LucideEyeOff,
  LucideLifeBuoy,
  LucideLoaderCircle,
  LucideLock,
  LucideTriangleAlert,
  LucideUser,
} from '@lucide/angular';

import { SessionStore } from '../../core/auth/session.store';
import { ApiError } from '../../core/http/api-error';

/**
 * Entrada na aplicação. Vive fora do `ShellComponent`, que pressupõe sessão.
 *
 * As credenciais são as do GEEA — as mesmas do Windows. Por isso não há
 * «lembrar-me»: o que ficaria guardado era a senha do domínio.
 */
@Component({
  selector: 'app-login-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    ReactiveFormsModule,
    LucideUser,
    LucideLock,
    LucideEye,
    LucideEyeOff,
    LucideLoaderCircle,
    LucideTriangleAlert,
    LucideLifeBuoy,
  ],
  template: `
    <div class="grid min-h-dvh lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
      <!-- Painel de marca: gradiente vermelho da marca a esmorecer para quase-preto,
           tal como a referência. Só em ecrãs largos — a duas colunas num telemóvel
           sobrava o formulário sem espaço. -->
      <div
        class="relative hidden overflow-hidden bg-gradient-to-br from-alert-500 via-alert-700 to-[#1a0604] lg:flex lg:flex-col lg:p-11"
      >
        <div
          aria-hidden="true"
          class="pointer-events-none absolute inset-0"
          style="background-image: radial-gradient(circle at 1px 1px, rgba(255,255,255,0.07) 1px, transparent 0); background-size: 26px 26px; mask-image: radial-gradient(65% 60% at 25% 20%, #000 0%, transparent 75%)"
        ></div>
        <div
          aria-hidden="true"
          class="pointer-events-none absolute -top-28 -right-20 size-80 rounded-full bg-alert-300/25 blur-3xl"
        ></div>
        <div
          aria-hidden="true"
          class="pointer-events-none absolute -bottom-24 -left-16 size-72 rounded-full bg-black/30 blur-3xl"
        ></div>

        <div
          class="relative inline-flex w-fit overflow-hidden rounded-xl p-[2.5px] shadow-lg shadow-black/30 motion-safe:animate-[card-in_400ms_cubic-bezier(0.22,1,0.36,1)]"
        >
          <!-- O gradiente cónico é maior do que a moldura e roda por baixo dela; o
               "overflow-hidden" acima recorta-o na forma arredondada, deixando só a
               linha a passar como uma luz a circundar o cartão. Duas camadas — uma
               desfocada por baixo a dar brilho, outra nítida por cima — para a linha
               não se perder contra o vermelho. -->
          <div
            aria-hidden="true"
            class="absolute inset-[-60%] blur-sm motion-safe:animate-[border-beam-spin_2.2s_linear_infinite]"
            style="background-image: conic-gradient(from 0deg, transparent 0%, rgba(255,255,255,0.9) 12%, transparent 30%)"
          ></div>
          <div
            aria-hidden="true"
            class="absolute inset-[-60%] motion-safe:animate-[border-beam-spin_2.2s_linear_infinite]"
            style="background-image: conic-gradient(from 0deg, transparent 0%, #fff 10%, transparent 24%)"
          ></div>
          <div
            class="relative inline-flex items-center rounded-[calc(0.75rem-2.5px)] bg-white px-3.5 py-2.5"
          >
            <img src="mozaops_logo_sem_fundo.svg" alt="MozaOps" class="h-5 w-auto" />
          </div>
        </div>

        <!-- Descreve a plataforma, não um módulo: cobre vários departamentos, não
             só Meios de Pagamento e Canais — esse é só o primeiro a estar pronto. -->
        <div
          class="relative mt-auto motion-safe:animate-[card-in_400ms_cubic-bezier(0.22,1,0.36,1)]"
        >
          <p class="text-xl leading-snug font-bold text-white">
            A plataforma de operações do Moza.
          </p>
          <p class="mt-3 max-w-sm text-sm text-white/70">
            Centraliza, acompanha e automatiza operações, num só lugar.
          </p>
        </div>
      </div>

      <!-- Formulário: ocupa o ecrã todo, sem cartão — a moldura já é a página. -->
      <div class="flex flex-col justify-center px-6 py-12 sm:px-12 lg:px-20 xl:px-28">
        <div
          class="mx-auto w-full max-w-sm motion-safe:animate-[card-in_400ms_cubic-bezier(0.22,1,0.36,1)]"
        >
          <img
            src="mozaops_logo_sem_fundo.svg"
            alt="MozaOps"
            class="mx-auto h-8 w-auto lg:hidden"
          />

          <h1 class="mt-8 text-center text-2xl leading-tight font-bold text-gray-900 lg:mt-0">
            Iniciar sessão
          </h1>
          <p class="mt-2 text-center text-sm text-gray-500">
            Introduza as suas credenciais para continuar.
          </p>

          @if (error()) {
            <p
              role="alert"
              class="mt-6 flex items-start gap-2 rounded-xl bg-alert-50 px-3.5 py-2.5 text-sm text-alert-700 ring-1 ring-alert-100 motion-safe:animate-[toast-in_220ms_cubic-bezier(0.16,1,0.3,1)]"
            >
              <svg
                lucideTriangleAlert
                [size]="16"
                [strokeWidth]="1.9"
                class="mt-0.5 shrink-0"
              ></svg>
              <span>{{ error() }}</span>
            </p>
          }

          <form class="mt-8 flex flex-col gap-4" [formGroup]="form" (ngSubmit)="submit()">
            <label class="flex flex-col gap-1.5">
              <span class="text-xs font-semibold text-gray-600">Utilizador</span>
              <div class="group relative">
                <svg
                  lucideUser
                  [size]="16"
                  [strokeWidth]="1.8"
                  class="pointer-events-none absolute top-1/2 left-3.5 -translate-y-1/2 text-gray-400 transition-colors group-focus-within:text-moza-600"
                ></svg>
                <input
                  formControlName="username"
                  autocomplete="username"
                  autocapitalize="none"
                  spellcheck="false"
                  autofocus
                  placeholder="m00xxxx"
                  class="w-full rounded-xl border border-gray-200 bg-gray-50/60 py-3 pr-3 pl-10 text-sm text-gray-900 outline-none transition-all placeholder:text-gray-400 hover:border-gray-300 focus:border-moza-400 focus:bg-white focus:ring-4 focus:ring-moza-100"
                />
              </div>
            </label>

            <label class="flex flex-col gap-1.5">
              <span class="text-xs font-semibold text-gray-600">Palavra-passe</span>
              <div class="group relative">
                <svg
                  lucideLock
                  [size]="16"
                  [strokeWidth]="1.8"
                  class="pointer-events-none absolute top-1/2 left-3.5 -translate-y-1/2 text-gray-400 transition-colors group-focus-within:text-moza-600"
                ></svg>
                <input
                  [type]="showPassword() ? 'text' : 'password'"
                  formControlName="password"
                  autocomplete="current-password"
                  (keyup)="trackCapsLock($event)"
                  (keydown)="trackCapsLock($event)"
                  placeholder="Introduza a sua palavra-passe"
                  class="w-full rounded-xl border border-gray-200 bg-gray-50/60 py-3 pr-10 pl-10 text-sm text-gray-900 outline-none transition-all placeholder:text-gray-400 hover:border-gray-300 focus:border-moza-400 focus:bg-white focus:ring-4 focus:ring-moza-100"
                />
                <button
                  type="button"
                  (click)="showPassword.set(!showPassword())"
                  [attr.aria-label]="
                    showPassword() ? 'Ocultar palavra-passe' : 'Mostrar palavra-passe'
                  "
                  class="absolute top-1/2 right-2 inline-flex size-7 -translate-y-1/2 items-center justify-center rounded-lg text-gray-400 transition-colors hover:bg-gray-100 hover:text-moza-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-moza-400"
                >
                  @if (showPassword()) {
                    <svg lucideEyeOff [size]="16" [strokeWidth]="1.8"></svg>
                  } @else {
                    <svg lucideEye [size]="16" [strokeWidth]="1.8"></svg>
                  }
                </button>
              </div>

              <!-- O domínio bloqueia a conta ao fim de algumas tentativas. -->
              @if (capsLock()) {
                <span class="flex items-center gap-1.5 text-2xs font-medium text-alert-600">
                  <svg lucideTriangleAlert [size]="13" [strokeWidth]="2" class="shrink-0"></svg>
                  Caps Lock está ligado
                </span>
              }
            </label>

            <!-- Não prender à validade do formulário: não é um signal, e numa
                 app zoneless o botão fica cinzento depois do autofill. -->
            <button
              type="submit"
              [disabled]="signingIn()"
              class="mt-2 inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-b from-alert-500 to-alert-600 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-alert-700/25 transition-all hover:from-alert-600 hover:to-alert-700 hover:shadow-alert-700/30 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-alert-300 disabled:cursor-not-allowed disabled:opacity-70"
            >
              @if (signingIn()) {
                <svg lucideLoaderCircle [size]="16" [strokeWidth]="2" class="animate-spin"></svg>
              }
              {{ signingIn() ? 'A entrar…' : 'Entrar' }}
            </button>
          </form>

          <div class="mt-8 flex items-center gap-2">
            <svg
              lucideLifeBuoy
              [size]="15"
              [strokeWidth]="1.9"
              class="shrink-0 text-gray-400"
            ></svg>
            <p class="text-xs text-gray-500">
              Precisa de ajuda?
              <a
                [href]="supportMailto"
                class="font-semibold text-moza-700 hover:text-moza-800 hover:underline"
              >
                Fale connosco
              </a>
            </p>
          </div>
        </div>
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
  protected readonly showPassword = signal(false);
  protected readonly capsLock = signal(false);

  protected trackCapsLock(event: KeyboardEvent): void {
    this.capsLock.set(event.getModifierState('CapsLock'));
  }

  protected readonly supportMailto =
    'mailto:dalton.chivambo@mozabanco.co.mz?subject=' +
    encodeURIComponent('MozaOps — Pedido de suporte técnico');

  protected async submit(): Promise<void> {
    if (this.signingIn()) return;

    if (this.form.invalid) {
      this.error.set('Preencha o utilizador e a palavra-passe.');
      return;
    }

    this.signingIn.set(true);
    this.error.set(null);

    const { username, password } = this.form.getRawValue();

    try {
      await this.session.signIn(username, password);
      this.form.reset();
      await this.router.navigateByUrl(this.destination());
    } catch (error) {
      this.error.set(
        error instanceof ApiError
          ? error.message
          : 'Ocorreu um erro inesperado. Se persistir, contacte o suporte.',
      );
    } finally {
      this.signingIn.set(false);
    }
  }

  private destination(): string {
    const returnUrl = new URLSearchParams(window.location.search).get('returnUrl');
    // Só caminhos relativos: um URL absoluto aqui seria um reencaminhamento aberto.
    return returnUrl?.startsWith('/') && !returnUrl.startsWith('//') ? returnUrl : '/';
  }
}
