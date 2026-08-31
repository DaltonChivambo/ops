# OWNERS

Mapa departamento → serviços. Governa a atribuição de revisores de PR no Bitbucket.
O departamento é **metadado** (`service.yaml`), não estrutura de pastas — ver
`docs/adr/0004-pastas-planas-departamento-como-metadado.md`.

| Serviço | Departamento | Owner | Porta | Schema |
|---|---|---|---|---|
| `auth` | Segurança / Plataforma | <equipa> | 8001 | `auth` |
| `ticketing` | Suporte e Service Desk | <equipa> | 8002 | `ticketing` |
| `asset` | Gestão de Ativos | <equipa> | 8003 | `asset` |
| `approval` | Plataforma (transversal) | <equipa> | 8004 | `approval` |
| `notification` | Plataforma (transversal) | <equipa> | 8005 | `notification` |
| `reporting` | Business Intelligence | <equipa> | 8006 | `reporting` |

## Componentes partilhados

| Caminho | Owner | Regra |
|---|---|---|
| `backend/libs/ops_common/` | Plataforma | Qualquer PR exige revisão da Plataforma. Só plumbing — nunca domínio nem modelos ORM partilhados. |
| `infra/` | Plataforma / DevOps | |
| `ci/` | DevOps | |
| `docs/adr/` | Arquitetura | Alteração estrutural exige ADR novo. |
