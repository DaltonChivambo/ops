# Meios de Pagamentos e Canais

**Departamento** — a pasta é a dele, por ser o agrupamento estável que o organigrama do
banco usa (ADR 0004). Não é, ele próprio, a unidade de acesso: dentro dele há unidades
orgânicas reais e distintas, e é a essas que o MozaOps dá acesso — a **área**, no
vocabulário do catálogo (`core/navigation.ts`: `AreaId`, `AREAS`, `NavModule.area`).

Hoje só uma ilha tem automação construída, e só ela é área: **Canais**
(`canais`, código GEEA `3230`, «Canais e Serviços de Integração»). Quem não for
desta área não vê as páginas dela, nem lhe chega pela API. «Meios de
Pagamentos» (`2442`, «Serviço de Meios de Pagamento») é outra unidade real, e
ganha a sua própria área no dia em que tiver a primeira automação.

## Ilhas

Três, tal como na barra lateral (`layout/sidebar.ts`):

- **Canais** (`channels/`) — POS, ATM, Quiosques. Contém as automações que servem os
  três, como `closing-credit-validation/`, e o aviso para os canais que ainda não têm
  nenhuma (`channel-placeholder.ts`). Entrar num canal com automação pronta
  abre-a directamente: quem trata disso é a `core/single-feature.guard.ts`.
  Houve aqui um catálogo de canal, com um cartão por automação — deixou de
  fazer sentido com uma automação por canal, e volta a fazer quando algum
  tiver duas.
- **Pagamentos** (`pagamentos` na barra lateral: Proc. de Salários, Cartões,
  Cheques) — ainda sem automação construída, por isso ainda sem pasta aqui, e
  ainda sem área própria: fica à boleia do acesso a Canais até ter a primeira.
- **Suporte e Monitorização de Fraudes** (`suporte-fraudes` na barra lateral,
  mostrado como "Fraudes" — o nome completo não cabe na largura da barra) —
  idem.

Pagamentos e Suporte e Monitorização de Fraudes ganham pasta própria
(`features/payments-and-channels/<ilha>/`) **e** área própria (`AreaId` novo,
`AUTH_AREAS` novo) quando tiverem a primeira automação — mesma regra do
catálogo: só está aqui o que existe.

## Acrescentar uma automação a uma ilha existente

Entra na pasta da ilha, ao lado das que já lá estão. Só justifica ilha nova
quando o agrupamento na barra lateral também for novo — e, se a ilha ainda não
tinha automação nenhuma, é o momento de lhe dar a sua própria área.
