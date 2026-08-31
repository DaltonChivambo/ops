# ops_common

**Só plumbing.** Nunca entidades de negócio nem modelos SQLAlchemy partilhados.

No dia em que dois serviços importarem a mesma tabela `Cliente` desta lib, deixam de poder fazer
deploy em separado e o resultado é um monólito distribuído — exatamente o problema que esta
arquitetura existe para evitar (secção 6 do `ARCHITECTURE.md`).

| Módulo | Responsabilidade |
|---|---|
| `config` | `BaseServiceSettings` — env vars comuns a todos os serviços |
| `auth` | verificação local do JWT contra o JWKS do Auth Service |
| `logging` | GELF → Graylog, com `correlation_id` em cada linha |
| `observability` | exportador Prometheus e middleware de métricas HTTP |
| `messaging` | cliente RabbitMQ, envelope de evento, publisher e consumer |
| `http` | error handlers, paginação, cliente que propaga o `X-Request-ID` |
| `testing` | fixtures partilhadas |

## Consumo

Contexto de build na raiz do monorepo, sem índice pip privado (ADR 0005):

    COPY backend/libs/ops_common /app/libs/ops_common
    RUN pip install -e /app/libs/ops_common

É isto que dá a mudança atómica: corrigir a validação do JWT toca a lib e os seis serviços num
só commit, num só PR, com um só build a validar tudo.
