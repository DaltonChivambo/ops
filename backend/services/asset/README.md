# Asset Management

Bounded context **Asset Management**. Cobre: inventário, ativos e licenças, mais o agendamento de manutenção (manutenção é sobre o ativo, muda com ele). Importação/exportação Excel não é serviço: é `infrastructure/external/excel/` aqui dentro.

## Perfil

HTTP + publisher + `scheduler.py` (manutenção agendada) — ver `ARCHITECTURE.md` §3.1.

Um serviço, um schema, uma pasta (ADR 0004). Se este contexto vier a precisar de um segundo
processo deployável, é uma decisão de arquitetura nova, não uma extensão silenciosa desta pasta.
