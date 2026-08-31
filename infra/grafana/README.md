# Grafana

Provisionado por ficheiro (`provisioning/`), versionado. Nada de configuração feita à mão na UI:
o que não estiver aqui perde-se no próximo `docker compose down -v`.

## Alerting → Ticketing

O alerting do Grafana faz **webhook** para o endpoint de entrada do Ticketing, que decide se abre
incidente. O Ticketing **não** faz polling ao Prometheus (secção 3 do `ARCHITECTURE.md`).

Contact point a criar (UI ou provisioning):

    Tipo: Webhook
    URL:  http://ticketing:8002/webhooks/grafana
    Header: X-Webhook-Token: <valor de TICKETING_GRAFANA_WEBHOOK_TOKEN>

O contrato do payload está em `backend/services/ticketing/src/ticketing/api/webhooks.py`.
