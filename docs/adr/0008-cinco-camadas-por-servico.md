# 0008 — Cinco camadas por serviço, com o vocabulário no domínio

- **Estado**: Aceite
- **Data**: 2026-09-02
- **Decisores**: Dalton Chivambo
- **Substitui**: a decisão de layout da [0006](0006-backend-mozaops-substitui-esqueletos.md)
  («`app/` — `routes → service → repository → models`»). O resto da 0006 — workspace `uv`,
  uma base e um role por serviço, Traefik, um Dockerfile único — **mantém-se**.
- **Mantém**: o critério da [0003](0003-estrutura-enxuta-em-vez-de-hexagonal.md) —
  *investir no que é caro de reverter, adiar o que é barato de acrescentar*. Este ADR não o
  revoga: aplica-o outra vez, com mais um ano de código à vista.

## Contexto

A 0006 aceitou o backend do MozaOps como ele veio, e escreveu porquê: «**copiou-se, não se
portou**», para não introduzir bugs em lógica bancária que já fechava contas. Foi a decisão
certa. O que este ADR regista é a fatura, que ficou visível assim que se leu o código com
atenção:

- **Duas coisas chamadas `models`** — `app/models.py` (tabelas SQLAlchemy) e
  `app/domain/models.py` (dataclasses puros). Quem lia um `import` não sabia qual era qual.
- **A persistência não estava numa camada**: `models.py` e `database.py` viviam na raiz de
  `app/`, ao lado das rotas.
- **O HTTP tinha entrado no domínio.** `app/errors.py` carregava `status = 422` e era
  importado por `infra/parsers.py` — um adaptador de Excel a saber códigos de protocolo.
- **O vocabulário do domínio estava escrito à mão em seis sítios.** Os cinco estados de
  validação apareciam como comentário (`Validation = str`), tuplo, `frozenset`, dicionário de
  contagens, dois mapas de rótulos e um `if`. Nada os obrigava a concordar: acrescentar um
  estado era encontrar seis sítios de cor, e esquecer um não dava erro nenhum.
- **Não havia um único modelo Pydantic**, apesar de a 0003 ter listado «DTOs Pydantic
  separados dos models SQLAlchemy» como decisão a **não** adiar. O contrato com o `models.ts`
  do SPA era garantido por um comentário.

O gatilho que a 0003 tinha definido para extrair `domain/` — «um serviço ganhar máquina de
estados ou regras densas» — já tinha disparado, e a 0006 reconheceu-o («a reconciliação tem
14 KB dela»). Faltava tirar as consequências no resto do serviço.

## Decisão

Cada serviço arruma-se em **cinco camadas irmãs** dentro de `app/`, que são as do
`docs/diagrams/camadas_microservice.png`:

```
app/
├── main.py            composition root: a app, o router, os handlers, o /health
├── settings.py        o que o serviço lê do ambiente — e só o que lê
├── pagination.py      value object partilhado, de camada nenhuma
├── controllers/       HTTP: rotas, schemas Pydantic, dependências, tradução de erros
├── services/          casos de uso
├── domain/            puro: vocabulário, modelos, regras
├── repositories/      o único acesso a dados; recebem a sessão, nunca a criam
└── infrastructure/    sessão, tabelas e os adaptadores de ficheiros
```

Com quatro regras que dão a estrutura:

1. **O sentido é único**: `controllers → services → repositories → infrastructure`. O `domain/`
   está no meio e não depende de ninguém.
2. **O vocabulário vive em `domain/vocabulary.py`**, em `StrEnum`, declarado uma vez. Os
   *rótulos* continuam a ser de cada camada — o relatório escreve «Fecho Não Creditado» e o
   JSON escreve `missing` —, mas indexados pelos membros do enum.
3. **Os erros do domínio não sabem o que é HTTP.** A tabela que os traduz em estado e código
   vive só em `controllers/error_handlers.py`, e é percorrida pela MRO.
4. **O Python é PEP 8; o contrato não muda.** Identificadores em snake_case, colunas e JSON em
   camelCase, com o nome explícito na coluna e o alias no schema.

### O que continua adiado, e com que gatilho

Esta é a secção que importa, e é a razão de este ADR existir: sem ela, a primeira pessoa a
chegar acrescenta as peças em falta «porque é boa prática», e o problema volta — que é
textualmente o que a 0003 avisou.

| Adiado | Gatilho de entrada |
|---|---|
| `ports/` com `Protocol` nos repositórios | Existir um segundo adaptador. Hoje há um por repositório: a interface seria escrita para um implementador só |
| `mappers.py` domínio ↔ ORM | Nunca por gosto. Traz a terceira representação do mesmo dado, que é o que a 0003 rejeitou |
| `value_objects/` | Invariante repetida que os `StrEnum` e os schemas não cubram |
| `core/container.py` | O `Depends()` deixar de chegar — **é** o contentor |
| `unit_of_work.py` | Transação que a sessão-por-request não cubra. O agregado da execução já grava numa só |
| `templates/service-template/` | Os serviços começarem a divergir — ao 3.º ou 4.º |
| Validador do `service.yaml` | O segundo serviço. Com um, não apanha nada |
| Testes de repositório contra Postgres | Um bug de SQL que os peça. Os de rota com duplo cobrem a arrumação |
| `.importlinter` | Chega revisão de código enquanto houver um serviço |

### Nomes na infraestrutura

A base, o role e o cliente Keycloak continuam a dizer `closing_reconciliation`. Renomeá-los
obriga a migrar a base com as execuções reais e a editar o `.env` de quem já corre isto — e
não é isso que este ADR trata. O que muda é que **os nomes antigos passam a estar todos
listados no `service.yaml`**, com os `ALTER` prontos, em vez de espalhados por comentários.

## Consequências

- Um conceito, um sítio. Acrescentar um estado de validação passa a ser uma linha em
  `domain/vocabulary.py`, e o resto do código ou já o conhece ou não compila.
- O contrato REST passa a ser declarado e verificado: quinze schemas no OpenAPI, e um teste que
  os confere contra o `models.ts`. Divergir do frontend passa a ser um teste vermelho em vez de
  uma descoberta tardia.
- **Custo assumido**: mais ficheiros, e um serviço pequeno passa a ter cinco pastas para o que
  cabia em quatro módulos. Vale a pena porque o `domain/` deste serviço não é pequeno.
- **Custo assumido**: a regra do sentido único fica dependente de revisão até haver
  `.importlinter`, tal como a 0003 registou.
- A refactorização foi feita em passos verificáveis, e não de uma vez. Cada um correu com o
  `make lint`, com os testes, e — nos que mexiam em serialização ou em nomes de campo — com um
  diff byte a byte das treze respostas HTTP e um `alembic revision --autogenerate` contra um
  Postgres a sério, que tem de devolver `pass`.

## Alternativas consideradas

**Manter o layout plano e corrigir só as colisões** (`models.py` → `tables.py`, repositórios em
classe). Era metade do benefício por um quinto do trabalho, e resolvia o sintoma mais visível.
Rejeitado porque deixava o vocabulário duplicado em seis sítios e o HTTP dentro do domínio, que
são os dois problemas que custam a sério — o primeiro por permitir divergência silenciosa, o
segundo por prender a camada de ficheiros ao protocolo.

**Hexagonal completo, com ports, adapters e mappers.** Rejeitado pela mesma razão da 0003, que
não mudou: três representações do mesmo dado mais um mapper, pagos em todos os campos, para
testar o domínio sem base de dados — que os testes de domínio com dados sintéticos já dão, sem
indirecção nenhuma.

**Renomear a base e o role a par do código.** Rejeitado por âmbito: é uma migração de dados
com janela própria, não uma arrumação de pastas. Fica registada no `service.yaml`.
