# OWNERS

Mapa serviço → área responsável. Governa a atribuição de revisores de PR.
A área é **metadado** (`service.yaml`), não estrutura de pastas — as pastas dos serviços são
por bounded context. A área é também a
unidade de **acesso**: a tabela de Serviços e o `AUTH_AREAS` do `.env` falam da mesma coisa.

**Área não é departamento.** «Meios de Pagamentos e Canais» é um departamento — o
agrupamento estável que dá nome à pasta do frontend — e dentro dele há várias áreas reais e
distintas (`channels`, `payments`). A tabela de Frontend organiza-se por
departamento, porque é a pasta que o operador de PR precisa de identificar; a de Serviços
organiza-se por área, porque é o que o `service.yaml` e o `AUTH_AREAS` declaram.

## Serviços

| Serviço | Contexto | Área | Owner | Porta | Base de dados |
|---|---|---|---|---|---|
| `business/reconciliation/pos-closing-credit-validation` | Validação de crédito de valores de fecho do POS | Canais | Dalton Chivambo | 8000 (8001 em dev) | `mozaops_pos_closing_credit_validation` |
| `platform/auth-service` | Sessões e áreas — autenticação contra o GEEA | — (transversal) | Dalton Chivambo | 8000 (8002 em dev) | — |

## Frontend

| Caminho | Departamento | Owner |
|---|---|---|
| `frontend/src/app/features/payments-and-channels/` | Meios de Pagamentos e Canais | \<equipa\> |
| `frontend/src/app/features/customers-and-accounts/` | Clientes e Contas | \<equipa\> |
| `frontend/src/app/{core,layout,shared}/` | Plataforma | \<equipa\> |

## Componentes partilhados

| Caminho | Owner | Regra |
|---|---|---|
| `backend/packages/` | Plataforma | Pacotes versionados. Só utilitários técnicos — nunca tabelas, nunca regra de negócio. Hoje: `mozaops-libs` (tokens do GEEA e mapa de áreas), usado pelos dois serviços. |
| `ci/` | Plataforma | Os scripts que qualquer pipeline chama; qualquer PR exige revisão da Plataforma. |
| `infra/`, `docker-compose*.yml` | Plataforma / DevOps | |
