# Notification

Bounded context **Notification**. Cobre: notificações por email e push. Genérico: consome eventos de todos os contextos.

## Perfil

Worker-first — o `main.py` só serve `/health` e `/metrics`; `worker.py` é o processo principal
(ver `ARCHITECTURE.md` §3.1).

Um serviço, um schema, uma pasta (ADR 0004). Se este contexto vier a precisar de um segundo
processo deployável, é uma decisão de arquitetura nova, não uma extensão silenciosa desta pasta.
