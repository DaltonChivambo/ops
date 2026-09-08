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

A pasta agrupa por **tipo de processo**, não por área nem por canal.

Uma área muda de nome e de perímetro mais depressa do que o código — por isso
`area` é um campo do `service.yaml` e não uma pasta. O mesmo vale para o canal:
POS, ATM e Quiosques são metadado, e a reconciliação de um fecho é o mesmo tipo
de trabalho nos três. Quem se organiza por área e ilha é o frontend, porque é a
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
| `service.yaml` | contrato legível por máquina — ver o esquema abaixo |
| `README.md` | o que faz, como se organiza, como se corre, e a tabela de responsabilidade |
| `app/` | as cinco camadas ([ADR 0008](../../docs/adr/0008-cinco-camadas-por-servico.md)) |
| `migrations/` | Alembic |
| `tests/` | |

### As cinco camadas

```
app/
├── main.py            composition root: a app, o router, os handlers, o /health
├── settings.py        o que o serviço lê do ambiente — e só o que lê
├── controllers/       HTTP: rotas, schemas, dependências, tradução de erros
├── services/          casos de uso
├── domain/            puro: sem FastAPI, sem SQLAlchemy, sem openpyxl
├── repositories/      o único acesso a dados; recebem a sessão, nunca a criam
└── infrastructure/    sessão, tabelas e os adaptadores de ficheiros
```

O sentido é único: `controllers → services → repositories → infrastructure`, com
o `domain/` no meio a não depender de ninguém. Um controlador nunca toca na base
de dados; um repositório nunca decide regra de negócio.

### O `service.yaml`

**Obrigatórios:**

| Campo | O que é |
|---|---|
| `name` | o nome do serviço, igual ao da pasta |
| `category` | a categoria de processo, igual à pasta acima |
| `context` | uma linha em português: o que a automação faz |
| `port` | a porta que o **contentor** escuta (a mesma do `EXPOSE` e do Traefik) |
| `database` · `role` | a base e o role Postgres próprios do serviço |
| `owner` | quem decide sobre o serviço e a quem se pergunta primeiro |

**Opcionais**, quando se aplicam:

| Campo | O que é |
|---|---|
| `dev_port` | a porta publicada em desenvolvimento, se diferente da `port` |
| `area` · `channels` | metadado — mudam mais depressa que o código. A `area` é também a unidade de acesso |
| `routes` | o caminho **público**, com o `/api` que o Traefik corta |
| `env_prefix` | quando o nome na infraestrutura difere do do serviço |
| `developed_by` · `requirements_by` | quem fez o trabalho, se não for o `owner` |

O `service.yaml` alimenta o [`OWNERS.md`](../../OWNERS.md) da raiz: ao mudar um
responsável, mudam-se os dois. **Não há ainda um validador** — com um serviço
não apanharia nada. Entra com o segundo, e nessa altura passa também a gerar o
`OWNERS.md` em vez de o duplicar à mão.
