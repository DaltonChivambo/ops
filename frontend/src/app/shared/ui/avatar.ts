/**
 * O disco com as iniciais de quem está autenticado.
 *
 * Constante e não componente porque os dois sítios que o usam tratam a
 * acessibilidade de maneira diferente: na barra lateral o rótulo está no botão
 * à volta, no cabeçalho está no próprio disco.
 */
export const AVATAR_CLASS =
  'grid size-9 shrink-0 place-items-center rounded-full bg-linear-to-br from-alert-500 ' +
  'to-alert-700 text-sm font-bold text-white shadow-sm ring-1 ring-white/20 ring-inset';
