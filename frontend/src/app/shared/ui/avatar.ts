/**
 * O disco com as iniciais de quem está autenticado.
 *
 * Vermelho da marca, o do logótipo. Aqui a chapa cheia assenta, ao contrário do
 * escudo do cabeçalho da página: um disco de 36px lê-se como identidade, não
 * como aviso.
 *
 * Gradiente e não cor lisa — o alert-500 sozinho num disco pequeno fica chapado.
 * Do 500 para o 700 dá-lhe volume sem virar decoração, e o anel interior branco
 * a 20% desenha-lhe o bordo, que de outra forma se perdia contra o branco da
 * barra.
 *
 * Constante e não componente porque os dois sítios que o usam tratam a
 * acessibilidade de maneira diferente — na barra lateral quem tem o rótulo é o
 * botão à volta, no cabeçalho é o próprio disco. Mesmo princípio dos STATE_CHIP
 * e STATE_STRIPE: o que se partilha é o aspecto, não a marcação.
 */
export const AVATAR_CLASS =
  'grid size-9 shrink-0 place-items-center rounded-full bg-linear-to-br from-alert-500 ' +
  'to-alert-700 text-sm font-bold text-white shadow-sm ring-1 ring-white/20 ring-inset';
