import type { Routes } from '@angular/router';

import { canAccess } from './core/auth/role.guard';
import { READERS } from './core/auth/roles';
import { ShellComponent } from './layout/shell';

/**
 * Rotas reais, com URL.
 *
 * O MozaOps v1 guardava a navegação num `useState` — não havia deep links, o
 * botão «voltar» do browser não funcionava e um F5 perdia o contexto. Os ids dos
 * módulos tinham sido desenhados para serem segmentos de URL e nunca lá
 * chegaram. Aqui chegam.
 */
export const routes: Routes = [
  {
    path: '',
    component: ShellComponent,
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'pos' },

      {
        path: 'sem-permissao',
        loadComponent: () =>
          import('./features/session/forbidden-page').then((m) => m.ForbiddenPageComponent),
      },

      {
        // `moduleId` liga-se ao input do componente por
        // `withComponentInputBinding()` — sem ActivatedRoute, sem subscrição.
        path: ':moduleId',
        canActivate: [canAccess(...READERS)],
        loadComponent: () =>
          import('./features/payments-and-channels/channels/channel-page').then(
            (m) => m.ChannelPageComponent,
          ),
      },

      {
        // A automação de um canal. Vem depois do catálogo por ser mais
        // específica; o `moduleId` diz qual canal, e é o mesmo ecrã para os três.
        path: ':moduleId/:featureId',
        canActivate: [canAccess(...READERS)],
        loadComponent: () =>
          import(
            './features/payments-and-channels/channels/closing-reconciliation/closing-reconciliation-page'
          ).then((m) => m.ClosingReconciliationPageComponent),
      },
    ],
  },

  { path: '**', redirectTo: '' },
];
