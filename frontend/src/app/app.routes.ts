import type { Routes } from '@angular/router';

import { canOpenModule } from './core/auth/area.guard';
import { openSingleFeature } from './core/single-feature.guard';
import { ShellComponent } from './layout/shell';

/** Rotas reais, com URL: os ids dos módulos são os segmentos. */
export const routes: Routes = [
  {
    // Fora do `ShellComponent`: a barra lateral e o menu de utilizador
    // pressupõem sessão, e não há nada a mostrar à volta de quem ainda não
    // entrou.
    path: 'login',
    loadComponent: () =>
      import('./features/session/login-page').then((m) => m.LoginPageComponent),
  },

  {
    path: '',
    component: ShellComponent,
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'pos' },

      {
        path: 'forbidden',
        loadComponent: () =>
          import('./features/session/forbidden-page').then((m) => m.ForbiddenPageComponent),
      },

      {
        // A openSingleFeature encurta o caminho: um canal com automação pronta
        // abre-a directamente, e só chega ao componente quem não tem nenhuma.
        path: ':moduleId',
        canActivate: [canOpenModule, openSingleFeature],
        loadComponent: () =>
          import('./features/payments-and-channels/channels/channel-placeholder').then(
            (m) => m.ChannelPlaceholderComponent,
          ),
      },

      {
        // Vem depois da rota curta por ser mais específica. Hoje só o POS lá
        // chega: o serviço expõe apenas /pos/validacao-credito-fecho.
        path: ':moduleId/:featureId',
        canActivate: [canOpenModule],
        loadComponent: () =>
          import('./features/payments-and-channels/channels/closing-credit-validation/closing-credit-validation-page').then(
            (m) => m.ClosingCreditValidationPageComponent,
          ),
      },
    ],
  },

  { path: '**', redirectTo: '' },
];
