import type { Routes } from '@angular/router';

import { canAccess } from './core/auth/role.guard';
import { READERS } from './core/auth/roles';
import { openSingleFeature } from './core/single-feature.guard';
import { ShellComponent } from './layout/shell';

/** Rotas reais, com URL: os ids dos módulos são os segmentos. */
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
        // A openSingleFeature encurta o caminho: um canal com automação pronta
        // abre-a directamente, e só chega ao componente quem não tem nenhuma.
        path: ':moduleId',
        canActivate: [canAccess(...READERS), openSingleFeature],
        loadComponent: () =>
          import('./features/payments-and-channels/channels/channel-placeholder').then(
            (m) => m.ChannelPlaceholderComponent,
          ),
      },

      {
        // Vem depois da rota curta por ser mais específica. Hoje só o POS lá
        // chega: o serviço expõe apenas /pos/validacao-credito-fecho.
        path: ':moduleId/:featureId',
        canActivate: [canAccess(...READERS)],
        loadComponent: () =>
          import('./features/payments-and-channels/channels/closing-reconciliation/closing-reconciliation-page').then(
            (m) => m.ClosingReconciliationPageComponent,
          ),
      },
    ],
  },

  { path: '**', redirectTo: '' },
];
