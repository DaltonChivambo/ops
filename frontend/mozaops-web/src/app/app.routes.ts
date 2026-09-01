import type { Routes } from '@angular/router';

import { canAccess } from './core/auth/role.guard';
import { READERS } from './core/auth/roles';
import { openSingleFeature } from './core/single-feature.guard';
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
        //
        // A openSingleFeature encurta o caminho: um canal com automação pronta
        // abre-a aqui mesmo, em vez de mostrar um catálogo com um cartão só. Só
        // chega ao componente quem ainda não tem nada para abrir.
        path: ':moduleId',
        canActivate: [canAccess(...READERS), openSingleFeature],
        loadComponent: () =>
          import('./features/payments-and-channels/channels/channel-placeholder').then(
            (m) => m.ChannelPlaceholderComponent,
          ),
      },

      {
        // A automação de um canal, e o destino real de quase toda a navegação:
        // é para aqui que a rota curta acima reencaminha. Vem depois dela por ser
        // mais específica. Hoje só o POS lá chega: a validação de fechos é dele,
        // e o serviço que a serve expõe apenas /pos/validacao-credito-fecho.
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
