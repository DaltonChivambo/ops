# Architecture Decision Records

Registo das decisões estruturais do MozaOps. Uma decisão por ficheiro, numerada por ordem
cronológica. Um ADR **não se reescreve** depois de aceite: quando uma decisão deixa de valer,
escreve-se um novo ADR que a substitui e marca-se o antigo como `Substituído por NNNN`.

O desenho resultante destas decisões está descrito em [`../../ARCHITECTURE.md`](../../ARCHITECTURE.md).

| # | Decisão | Estado | Data |
|---|---|---|---|
| [0001](0001-monorepo-unico.md) | Monorepo único | Aceite | 2026-08-25 |
| [0002](0002-decomposicao-por-bounded-context.md) | Decomposição por bounded context | Substituído por 0006 | 2026-08-25 |
| [0003](0003-estrutura-enxuta-em-vez-de-hexagonal.md) | Estrutura enxuta em vez de hexagonal completo | Substituído por 0006 | 2026-08-25 |
| [0004](0004-pastas-planas-departamento-como-metadado.md) | Pastas planas, departamento como metadado | Aceite | 2026-08-25 |
| [0005](0005-ops-common-com-contexto-de-build-na-raiz.md) | `ops_common` com contexto de build na raiz | Substituído por 0006 | 2026-08-25 |
| [0006](0006-backend-mozaops-substitui-esqueletos.md) | O backend do MozaOps substitui os esqueletos da plataforma | Aceite | 2026-08-31 |
| [0007](0007-federacao-ldap.md) | Federação LDAP/AD no Keycloak | Substituído por 0009 | 2026-08-02 |
| [0008](0008-cinco-camadas-por-servico.md) | Cinco camadas por serviço, com o vocabulário no domínio | Aceite | 2026-09-02 |
| [0009](0009-autenticacao-contra-o-geea.md) | Autenticação contra o GEEA, sem Keycloak próprio | Aceite | 2026-09-06 |

O 0001 e o 0004 mantêm-se: o monorepo continua único, e o departamento continua metadado e
não estrutura de pastas.

O 0009 substitui o 0007 por inteiro: não há Keycloak nosso para federar, e por isso os
grupos do AD que o 0007 mapeava deixaram de ter onde ser mapeados.

O 0008 substitui **só a decisão de layout** da 0006 — o resto dela (workspace `uv`, uma base
e um role por serviço, Traefik, Dockerfile único) continua a valer, e por isso a 0006 fica
**Aceite** e não substituída. É a primeira vez que um ADR substitui parte de outro; quando
voltar a acontecer, é assim que se regista.

## Formato

```markdown
# NNNN — Título na forma de decisão

- **Estado**: Proposto | Aceite | Substituído por NNNN
- **Data**: AAAA-MM-DD
- **Decisor(es)**: ...

## Contexto
O que era verdade quando a decisão foi tomada, e que problema forçou a escolha.

## Decisão
O que foi decidido, no imperativo.

## Consequências
O que passa a ser verdade — incluindo o que fica pior.

## Alternativas consideradas
O que foi rejeitado e porquê. É esta secção que evita voltar a discutir o mesmo daqui a um ano.
```
