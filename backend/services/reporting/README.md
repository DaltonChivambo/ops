# Reporting

Bounded context **Reporting**. Cobre: relatórios e auditoria. Read-only e eventualmente consistente: constrói o próprio schema denormalizado a partir de eventos e nunca lê os schemas dos outros.

## Perfil

Worker-first — o `main.py` serve `/health`, `/metrics` e as leituras; `worker.py` é o processo
principal (ver `ARCHITECTURE.md` §3.1).

Um serviço, um schema, uma pasta (ADR 0004). Se este contexto vier a precisar de um segundo
processo deployável, é uma decisão de arquitetura nova, não uma extensão silenciosa desta pasta.
