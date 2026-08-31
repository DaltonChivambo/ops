# Graylog

Recebe logs GELF em UDP/12201, emitidos por `ops_common.logging`. Cada linha leva o
`correlation_id` (o `X-Request-ID` injetado pelo OSB), que é o que permite seguir um pedido
entre o OSB, o Auth e o serviço de negócio.

## Input a criar no primeiro arranque

System → Inputs → **GELF UDP** → Launch new input → porta `12201`, bind `0.0.0.0`.
(É a única ação manual do arranque; o resto é provisionado.)

## Pesquisa típica

    correlation_id:"3f1c2b7e-..."            # o pedido inteiro, ponta a ponta
    service:asset AND level:<=3              # erros do Asset
    event_name:ativo.criado                  # rasto de um evento no barramento
