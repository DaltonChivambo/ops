# OWNERS

Mapa serviço → departamento responsável. Governa a atribuição de revisores de PR.
O departamento é **metadado** (`service.yaml`), não estrutura de pastas — as pastas dos
serviços são por bounded context. Quem se organiza por departamento é o frontend, porque é a
navegação que o operador vê.

## Serviços

| Serviço | Contexto | Departamento | Owner | Porta | Base de dados |
|---|---|---|---|---|---|
| `reconciliation/closing-credit-validation` | Validação de crédito de valores de fecho | Meios de Pagamentos e Canais | Dalton Chivambo | 8000 (8001 em dev) | `mozaops_closing_reconciliation` |
| `platform/identity` | Sessões e papéis — autenticação contra o GEEA | — (transversal) | Dalton Chivambo | 8000 (8002 em dev) | — |

## Frontend

| Caminho | Departamento | Owner |
|---|---|---|
| `frontend/src/app/features/payments-and-channels/` | Meios de Pagamentos e Canais | \<equipa\> |
| `frontend/src/app/features/customers-and-accounts/` | Clientes e Contas | \<equipa\> |
| `frontend/src/app/{core,layout,shared}/` | Plataforma | \<equipa\> |

## Componentes partilhados

| Caminho | Owner | Regra |
|---|---|---|
| `backend/libs/` | Plataforma | Só utilitários técnicos — nunca tabelas, nunca regra de negócio. Hoje: `auth` (tokens do GEEA e mapa de papéis), partilhado pelos dois serviços. |
| `backend/Dockerfile`, `backend/pyproject.toml`, `backend/uv.lock` | Plataforma | Servem todos os serviços; qualquer PR exige revisão da Plataforma. |
| `infra/`, `docker-compose*.yml` | Plataforma / DevOps | |
| `docs/adr/` | Arquitetura | Alteração estrutural exige ADR novo. Um ADR aceite não se reescreve — substitui-se. |
