# 0004 — Pastas planas, departamento como metadado

- **Estado**: Aceite
- **Data**: 2026-08-25
- **Decisores**: Dalton Chivambo

## Contexto

Os serviços destinam-se à Direção de Operações e cada um tem um departamento responsável. A
pergunta era se `backend/services/` deveria refletir essa estrutura organizacional no caminho
das pastas.

Com a decomposição por bounded context ([0002](0002-decomposicao-por-bounded-context.md)) a
questão perdeu força — mas não desapareceu, porque continua a ser preciso saber quem é dono de
cada serviço.

## Decisão

Pastas planas, uma por bounded context:

```
backend/services/
├── auth/
├── ticketing/
├── asset/
├── approval/
├── notification/
└── reporting/
```

O departamento e o responsável vivem no `service.yaml` de cada serviço, junto com a porta, o
schema e o contrato de eventos:

```yaml
name: asset
port: 8003
schema: asset
department: Gestão de Ativos
owner: <equipa>
publishes: [ativo.criado, ativo.actualizado]
consumes: []
```

Um `OWNERS.md` na raiz agrega o mapa departamento → serviços e governa as revisões de PR.

## Consequências

- Uma reorganização de departamentos — fusão, mudança de nome, troca de responsável — é **uma
  linha de YAML**, não um `git mv` que arrasta o nome da imagem Docker, o `context:` do compose,
  o caminho no Jenkinsfile, a rota no OSB e o histórico do git.
- Os `service.yaml` são legíveis por script: alimentam `docs/registry.md`, a geração do compose,
  os scrape jobs do Prometheus e a deteção de eventos órfãos quando um contrato muda.
- Serviços transversais como o `approval` e o `notification`, que não pertencem a um único
  departamento, deixam de precisar de uma pasta artificial onde viver.
- **Custo**: a árvore de pastas já não mostra de imediato quem é dono de quê. Mitigado pelo
  `OWNERS.md` e pelo `service.yaml`.

## Alternativas consideradas

**Pastas aninhadas por departamento** (`services/<departamento>/<servico>/`). Dá navegação
alinhada com a organização e permissões Bitbucket por pasta. Rejeitado porque o organigrama muda
mais depressa que o código, e cada mudança propagaria por caminhos, nomes de imagem e pipelines.

**Gatilho para reconsiderar**: cada departamento passar a ter equipa de desenvolvimento própria e
serem precisas permissões Bitbucket por pasta. Aí o custo do aninhamento passa a compensar.
