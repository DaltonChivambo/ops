# Meios de Pagamentos e Canais

Departamento **Meios de Pagamentos e Canais**. As automações agrupam-se por ilha — o
mesmo agrupamento que a barra lateral mostra (`layout/sidebar.ts`) e que
`core/navigation.ts` descreve (`DEPARTMENTS`, `NavModule.department`).

## Ilhas

Três, tal como na barra lateral (`layout/sidebar.ts`):

- `channels/` — POS, ATM, Quiosques. Contém o catálogo genérico de canal
  (`channel-page.ts`) e as automações que servem os três, como
  `closing-reconciliation/`.
- **Pagamentos** (`pagamentos` na barra lateral: Proc. de Salários, Cartões,
  Cheques) — ainda sem automação construída, por isso ainda sem pasta aqui.
- **Suporte e Monitorização de Fraudes** (`suporte-fraudes` na barra lateral,
  mostrado como "Fraudes" — o nome completo não cabe na largura da barra) —
  idem.

Pagamentos e Suporte e Monitorização de Fraudes ganham pasta própria
(`features/payments-and-channels/<ilha>/`) quando tiverem a primeira automação
— mesma regra do catálogo: só está aqui o que existe.

## Acrescentar uma automação a uma ilha existente

Entra na pasta da ilha, ao lado das que já lá estão. Só justifica ilha nova
quando o agrupamento na barra lateral também for novo.
