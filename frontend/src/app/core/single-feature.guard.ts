import { inject } from '@angular/core';
import { Router, type CanActivateFn } from '@angular/router';

import { findModule } from './navigation';

/**
 * Um canal com automação a funcionar abre-a de imediato.
 *
 * Reencaminhamento e não mudança dos destinos da barra lateral, para o endereço
 * curto continuar a valer. Quando um canal tiver duas automações, volta a fazer
 * falta um ecrã para escolher.
 */
export const openSingleFeature: CanActivateFn = (route) => {
  const moduleId = route.paramMap.get('moduleId') ?? '';
  const feature = findModule(moduleId)?.features.find((item) => item.available);

  // Sem automação pronta (ATM, Quiosques, Dashboard) segue para o aviso.
  return feature ? inject(Router).createUrlTree(['/', moduleId, feature.id]) : true;
};
