# Serviços

Um serviço por automação, agrupados por **categoria de processo**:

```
services/<categoria>/<serviço>/
```

Hoje:

| Categoria | Serviços |
|---|---|
| [`reconciliation/`](reconciliation/) | [`closing-credit-validation`](reconciliation/closing-credit-validation/) — validação de crédito de valores de fecho de POS |

## Porquê categorias, e porquê estas

A pasta agrupa por **tipo de processo**, não por departamento nem por canal.

Um departamento muda de nome e de perímetro mais depressa do que o código, e a
mesma automação pode servir mais do que um — por isso `departments` é um campo
do `service.yaml` e não uma pasta. O mesmo vale para o canal: POS, ATM e
Quiosques são metadado, e a reconciliação de um fecho é o mesmo tipo de trabalho
nos três. Quem se organiza por departamento e ilha é o frontend, porque é a
navegação que o operador vê.

O que muda devagar é a natureza do processo — reconciliar é reconciliar. É isso
que dá uma pasta estável.

## Acrescentar um serviço

**Numa categoria existente**, é criar a pasta lá dentro. O `uv` apanha-o
sozinho: o workspace tem `members = ["libs", "services/*/*"]`.

**Categoria nova** só quando houver um processo que não caiba em nenhuma —
e com pelo menos um serviço a entrar já. Uma pasta de categoria vazia, ou com um
serviço que ainda não existe, é uma promessa que aparece em buscas e engana quem
vier a seguir. A regra do repositório é a mesma em toda a parte: só está aqui o
que existe.

Categorias prováveis quando o trabalho aparecer — não as criar antes disso:
processamento (salários, ficheiros de pagamento), monitorização (fraude,
alertas), cadastro.

## O que cada serviço tem de trazer

| | |
|---|---|
| `service.yaml` | contrato legível por máquina: nome, categoria, porta, base, rotas e **quem responde por ele** |
| `README.md` | o que faz, como se organiza, como se corre, e a tabela de responsabilidade |
| `app/` | `routes → service → repository`, com `domain/` puro e `infra/` à parte |
| `migrations/` | Alembic |
| `tests/` | |

O `service.yaml` alimenta o [`OWNERS.md`](../../OWNERS.md) da raiz: ao mudar um
responsável, mudam-se os dois.
