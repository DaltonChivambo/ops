# OWNERS

Mapa serviço → departamento responsável. Governa a atribuição de revisores de PR.
O departamento é **metadado** (`service.yaml`), não estrutura de pastas — as pastas dos
serviços são por bounded context. Quem se organiza por departamento é o frontend, porque é a
navegação que o operador vê.

## Serviços

| Serviço | Contexto | Departamento | Owner | Porta | Base de dados |
|---|---|---|---|---|---|
| `closing-reconciliation` | Conciliação de fechos | Meios de Pagamentos e Canais | \<equipa\> | 8001 | `mozaops_closing_reconciliation` |

## Frontend

| Caminho | Departamento | Owner |
|---|---|---|
| `frontend/mozaops-web/src/app/features/payments-and-channels/` | Meios de Pagamentos e Canais | \<equipa\> |
| `frontend/mozaops-web/src/app/features/customers-and-accounts/` | Clientes e Contas | \<equipa\> |
| `frontend/mozaops-web/src/app/{core,layout,shared}/` | Plataforma | \<equipa\> |

## Componentes partilhados

| Caminho | Owner | Regra |
|---|---|---|
| `backend/libs/` | Plataforma | Só utilitários técnicos — nunca tabelas, nunca regra de negócio. Entra no dia em que houver segundo consumidor. |
| `backend/Dockerfile`, `backend/pyproject.toml`, `backend/uv.lock` | Plataforma | Servem todos os serviços; qualquer PR exige revisão da Plataforma. |
| `infra/`, `docker-compose*.yml` | Plataforma / DevOps | |
| `docs/adr/` | Arquitetura | Alteração estrutural exige ADR novo. Um ADR aceite não se reescreve — substitui-se. |
