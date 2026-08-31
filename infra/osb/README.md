# Oracle Service Bus

Configuração e rotas exportadas do OSB, versionadas aqui. O OSB é o gateway: roteia, faz o corte
grosso de autenticação e injeta o `X-Request-ID`. **Não é o único ponto de verificação do JWT** —
cada serviço valida o token localmente contra o JWKS do Auth (secção 6 do `ARCHITECTURE.md`).

## Rotas

| Caminho público | Destino interno |
|---|---|
| `/api/v1/auth/**`          | `http://auth:8001/api/v1/**` |
| `/api/v1/tickets/**`       | `http://ticketing:8002/api/v1/**` |
| `/api/v1/ativos/**`        | `http://asset:8003/api/v1/**` |
| `/api/v1/manutencoes/**`   | `http://asset:8003/api/v1/**` |
| `/api/v1/pedidos/**`       | `http://approval:8004/api/v1/**` |
| `/api/v1/notificacoes/**`  | `http://notification:8005/api/v1/**` |
| `/api/v1/relatorios/**`    | `http://reporting:8006/api/v1/**` |

## Responsabilidades

1. Terminação TLS.
2. `X-Request-ID`: gera se não vier do cliente; propaga sempre.
3. Rejeita pedidos sem `Authorization: Bearer` (exceto `/api/v1/auth/login` e `/api/v1/auth/.well-known/jwks.json`).
4. Health check dos destinos em `/health` (fora do `/api/v1`).
5. Timeouts: 30s por defeito. Uploads de Excel respondem `202` de imediato — não é preciso alargar.

## Exportar / importar

    # exportar do ambiente (script do OSB), guardar em osb/exports/<data>/
    # importar num ambiente novo a partir do último export versionado
