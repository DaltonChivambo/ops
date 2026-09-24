# Serviços

Um serviço por automação, agrupados por **categoria de processo**:

```
services/<categoria>/<serviço>/
```

`business/` tem uma subcategoria a mais — `services/business/<subcategoria>/<serviço>/` —
porque é aí que vivem as automações de regra de negócio, e uma só subcategoria não chega para
as distinguir por tipo de processo. As outras categorias ficam nos dois níveis de sempre.

Hoje:

| Categoria | Serviços |
|---|---|
| [`business/reconciliation/`](business/reconciliation/) | [`pos-closing-credit-validation`](business/reconciliation/pos-closing-credit-validation/) — validação de crédito de valores de fecho do POS |

## Porquê categorias, e porquê estas

A pasta agrupa por **tipo de processo**, não por área.

Uma área muda de nome e de perímetro mais depressa do que o código — por isso
`area` é um campo do `service.yaml` e não uma pasta. Quem se organiza por área e
ilha é o frontend, porque é a navegação que o operador vê.

O que muda devagar é a natureza do processo. `reconciliar` é um desses processos
estáveis, e vive dentro de `business/` porque é uma das várias categorias de
negócio que hão-de aparecer — `pos-closing-credit-validation` é específico do
POS, de propósito: decidiu-se que ATM e Quiosques vão ganhar serviços próprios
quando chegar a vez, em vez de partilhar este, por isso já não fazia sentido um
serviço a prometer servir os três canais.

## Acrescentar um serviço

**Numa (sub)categoria existente**, é criar a pasta lá dentro, com o `Dockerfile` e o
`pyproject.toml` do serviço mais parecido como ponto de partida. O `make check` descobre-o
pelo `Dockerfile`, sem editar nada fora da pasta. No `docker-compose.yml`, o bloco do serviço leva
`extra_hosts: *geea-host`, como os outros: é o que o deixa chegar ao GEEA na rede do banco.

**Categoria nova** só quando houver um processo que não caiba em nenhuma —
e com pelo menos um serviço a entrar já. Uma pasta de categoria vazia, ou com um
serviço que ainda não existe, é uma promessa que aparece em buscas e engana quem
vier a seguir. A regra do repositório é a mesma em toda a parte: só está aqui o
que existe.

Subcategorias prováveis dentro de `business/` quando o trabalho aparecer — não
as criar antes disso: processamento (salários, ficheiros de pagamento),
monitorização (fraude, alertas), cadastro.

## O que cada serviço tem de trazer

| | |
|---|---|
| `service.yaml` | contrato legível por máquina — ver o esquema abaixo |
| `Dockerfile` | a imagem do serviço, com a pasta como contexto de build |
| `pyproject.toml` · `uv.lock` | dependências, versão do Python e configuração do ruff e do mypy |
| `requirements.txt` · `requirements-dev.txt` | exportados do lock, com hashes: o que a imagem instala |
| `wheels/` | os pacotes internos, na versão que o serviço usa |
| `README.md` | o que faz, como se organiza, como se corre, a tabela de responsabilidade, e «Na rede do banco: onde se mexe» |
| `app/` | as cinco camadas — ver o `ARCHITECTURE.md` |
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
| `dev_port` | a porta publicada em desenvolvimento: `platform` a partir da 8010, `business` a partir da 8101, a seguinte livre |
| `area` · `channels` | metadado — mudam mais depressa que o código. A `area` é também a unidade de acesso |
| `routes` | o caminho **público**, com o `/api` que o Traefik corta |
| `env_prefix` | quando o nome na infraestrutura difere do do serviço |
| `developed_by` · `requirements_by` | quem fez o trabalho, se não for o `owner` |

O `service.yaml` alimenta o [`OWNERS.md`](../../OWNERS.md) da raiz: ao mudar um
responsável, mudam-se os dois. **Não há ainda um validador** — com um serviço
não apanharia nada. Entra com o segundo, e nessa altura passa também a gerar o
`OWNERS.md` em vez de o duplicar à mão.
