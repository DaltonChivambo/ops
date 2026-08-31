# Ticketing

Bounded context **Ticketing**. Cobre: tickets, incidentes e atribuição. Recebe o webhook de alertas do Grafana e decide se abre incidente — não faz polling ao Prometheus.

## Perfil

HTTP + publisher + consumidor do snapshot de ativo — ver `ARCHITECTURE.md` §3.1.

Um serviço, um schema, uma pasta (ADR 0004). Se este contexto vier a precisar de um segundo
processo deployável, é uma decisão de arquitetura nova, não uma extensão silenciosa desta pasta.
