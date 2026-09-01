import { inject } from '@angular/core';
import { Router, type CanActivateFn } from '@angular/router';

import { findModule } from './navigation';

/**
 * Um canal que tenha automação a funcionar abre-a de imediato.
 *
 * Havia aqui um catálogo: o canal mostrava as suas funcionalidades em cartões e
 * pedia um clique em «Abrir». Com uma funcionalidade por canal — e é uma só —
 * o catálogo era um ecrã inteiro para escolher entre uma opção.
 *
 * Fica como reencaminhamento e não como alteração dos destinos da barra lateral
 * para o endereço curto continuar a valer: `/pos` é o que está nos favoritos de
 * quem já usa isto, e continua a chegar ao sítio certo.
 *
 * Quando um canal ganhar uma segunda automação, é aqui que o catálogo volta a
 * fazer sentido — e volta a ser preciso um ecrã para escolher.
 */
export const openSingleFeature: CanActivateFn = (route) => {
  const moduleId = route.paramMap.get('moduleId') ?? '';
  const feature = findModule(moduleId)?.features.find((item) => item.available);

  // Sem automação pronta (ATM, Quiosques, Dashboard) segue para o aviso.
  return feature ? inject(Router).createUrlTree(['/', moduleId, feature.id]) : true;
};
