# 0003 — Estrutura enxuta em vez de hexagonal completo

- **Estado**: Substituído por [0006](0006-backend-mozaops-substitui-esqueletos.md)
- **Data**: 2026-08-25
- **Decisores**: Dalton Chivambo

> Este é o ADR mais importante do conjunto. Sem ele, a primeira pessoa a chegar acrescenta as
> peças em falta "porque é boa prática", e o problema volta.

## Contexto

O diagrama de camadas de partida (`docs/diagrams/camadas_microservice.png`) definia
`controllers → services → (domain/ + infrastructure/) → repositories`, com a regra de que só os
controllers dependem do FastAPI.

Uma primeira proposta de estrutura levava isso até ao fim, em todos os seis serviços e desde o
dia um: `domain/entities/`, `domain/value_objects/`, `domain/ports/` com interfaces,
`infrastructure/.../repositories/` como adapters, `mappers.py` para converter entre entidade e
model ORM, `core/container.py` como composition root, `unit_of_work.py` como fronteira
transacional, padrão outbox, import-linter e cookiecutter.

Essa proposta foi questionada como over-engineering. A revisão confirmou-o: os serviços em causa
são, na sua maioria, CRUD com importação de Excel e workflows de aprovação — não têm regra de
negócio densa que justifique o custo.

Com hexagonal completo, o mesmo dado passa a ter **três representações** — entidade de domínio,
model SQLAlchemy e schema Pydantic — mais um mapper a manter. Cada campo novo toca em quatro
sítios.

## Decisão

Adotar a estrutura descrita em `ARCHITECTURE.md` §4:

```
src/<servico>/
├── main.py
├── core/              config.py · security.py · exceptions.py · logging.py
├── api/
│   ├── health.py      /health · /ready — fora de /v1
│   ├── error_handler.py
│   └── v1/            router.py · controllers/ · schemas/ · dependencies.py
├── services/          casos de uso
└── infrastructure/
    ├── persistence/   session.py · models/ · repositories/
    ├── messaging/     publisher e/ou consumers
    ├── files/excel/
    └── external/
```

O critério que a governa: **investir no que é caro de reverter, adiar o que é barato de
acrescentar.**

### Fica desde já — caro de reverter

| Decisão | Porquê não se adia |
|---|---|
| Um schema **e um role** Postgres por serviço | A única que não se retrofita: quando dois serviços partilham tabelas, separá-los passa a ser um projeto de meses |
| `/api/v1/` no caminho | Acrescentar versionamento depois obriga a mexer no OSB e no Angular |
| DTOs Pydantic separados dos models SQLAlchemy | Expor colunas da BD no JSON prende o contrato REST ao esquema de tabelas |
| Correlation-id nos logs | Sem ele o Graylog não consegue seguir um pedido entre serviços; custa ~15 linhas |

### Fica de fora — com gatilho de entrada definido

| Adiado | Gatilho |
|---|---|
| `domain/entities/`, `ports/`, `mappers.py` | Um serviço ganhar máquina de estados ou regras densas — provavelmente Ticketing ou Approval |
| `value_objects/` | Invariante repetida que a validação Pydantic não cubra |
| `core/container.py` | O `Depends()` do FastAPI deixar de chegar — **já é** o contentor de DI |
| `unit_of_work.py` | Transação que a sessão-por-request não cubra |
| Padrão outbox | A primeira perda de evento custar mais que a tabela e o poller extra |
| `.importlinter` | Existirem camadas suficientes para valer a pena proteger — chega com o `domain/` |
| `tests/contract/` (schemathesis) | O frontend Angular começar a consumir a API a sério |
| `templates/service-template/` | Os serviços começarem a divergir — tipicamente ao 3.º ou 4.º |

`worker.py` e `messaging/` **não** estão adiados: o Notification e o Reporting existem para
consumir eventos (ver [0002](0002-decomposicao-por-bounded-context.md)).

## Consequências

- Menos código por serviço, menos indireção, e um serviço novo arranca mais depressa.
- A atomicidade entre repositórios é garantida por **sessão-por-request**: `dependencies.get_db`
  abre a Session, o controller injeta-a, commit no fim. Os repositórios **recebem** a Session e
  nunca criam a sua — esta regra não é opcional, é o que substitui a Unit of Work.
- **Extrair hexagonal mais tarde faz-se num serviço só**, sem tocar nos outros. É o oposto do
  isolamento de dados, que tem de estar certo à partida — e é por isso que o custo de adiar é
  baixo.
- **Custo**: sem `.importlinter`, a regra "só a camada `api/` importa FastAPI" fica dependente de
  revisão de código até haver `domain/`.
- **Custo**: os models SQLAlchemy servem de representação de persistência e de domínio. Num
  serviço que ganhe regras densas, isso torna-se limitante — e é precisamente o sinal de que
  chegou a hora de extrair `domain/` nesse serviço.

## Nota sobre o diagrama de partida

No `camadas_microservice.png` as setas vão `services → domain → repositories`, o que faz o
domínio depender para baixo. Quando um serviço ganhar `domain/`, a dependência deve ser
**invertida**: o domínio define as interfaces, a infraestrutura implementa-as. O diagrama deve
ser corrigido nessa altura.

## Alternativas consideradas

**Hexagonal completo em todos os serviços desde o dia um.** Rejeitado como over-engineering para
serviços maioritariamente CRUD: três representações do mesmo dado mais um mapper, pagos em todos
os campos de todos os serviços, para um benefício — testar o domínio sem base de dados — que os
testes de integração contra o Postgres em Docker já dão, e com mais fidelidade.

**Hexagonal só nos serviços com workflow (Ticketing, Approval), enxuto nos restantes, decidido à
partida.** Rejeitado por ser prematuro: não se sabe ainda quais serviços vão ganhar regras densas.
A decisão fica adiada até o próprio código a tornar óbvia, com o gatilho registado acima.
