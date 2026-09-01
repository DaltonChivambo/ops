# MozaOps

Plataforma de automações operacionais do **Moza Banco** — Departamento de Meios de Pagamento
e Canais (DOP).

Substitui o fecho manual em Excel — exportar do Portal SIMO, do Banka e do MIS e cruzar à mão
com `VLOOKUP` — por execuções auditáveis e persistidas. Cada processo do departamento é uma
**automação**: um módulo com a sua página, as suas regras e as suas tabelas.

- **[`ARCHITECTURE.md`](ARCHITECTURE.md)** — o que o sistema é: camadas, decomposição, infraestrutura.
- **[`docs/adr/`](docs/adr/README.md)** — as decisões que custaram a tomar, e porquê.
- **[`OWNERS.md`](OWNERS.md)** — quem é dono de quê.

## Arquitectura, em cinco linhas

Monorepo. Backend FastAPI em workspace `uv`, com uma base de dados e um role por serviço, sem
acesso à do outro. Frontend Angular 22. Traefik como entrada única — o que faz com que o SPA e
a API partilhem origem e não exista CORS nenhum para configurar. Keycloak para identidade, já
de pé mas **ainda não ligado**. Tudo em Docker Compose.

## Estado

| | |
|---|---|
| `closing-reconciliation` (POS) | construído — parse, reconciliação, persistência e relatório |
| Autenticação | **por ligar**: as rotas estão abertas e o frontend corre com sessão de desenvolvimento |
| Canais ATM e Quiosques | por fazer (é a mesma automação, muda o ficheiro de entrada) |
| Serviço `cases` | por fazer |
| CI | por fazer |

## Pré-requisitos

| | Versão | Notas |
|---|---|---|
| Docker | ≥ 25, com Compose v2 | traz o `uv` e o Python — não é preciso instalá-los |
| Node | ≥ 22.22.3 (usamos 24 LTS) | só para o frontend. O Angular 22 não instala com menos |

## Arrancar

```bash
cp .env.example .env     # ajustar as senhas
make up                  # traefik, postgres, keycloak, otel, jaeger e os serviços
make migrate             # alembic upgrade head
```

E o frontend, noutro terminal:

```bash
cd frontend && npm install && npm start   # http://localhost:4200
```

`*.localhost` resolve para 127.0.0.1 sem tocar no `/etc/hosts`:

| | |
|---|---|
| Aplicação (dev) | http://localhost:4200 |
| API (dev, direto) | http://localhost:8001 |
| Keycloak | http://sso.mozaops.localhost |
| Jaeger | http://jaeger.mozaops.localhost |
| Painel do Traefik | http://127.0.0.1:8080 |

```bash
make            # lista os comandos
make test       # testes do backend
make down       # pára, mantendo os dados
```

> **`make clean` apaga os volumes.** A base local pode ter execuções reais do departamento.
> Não é comando para correr por hábito.

## Convenções

**Tudo em inglês, excepto o que o operador lê.** Pastas, ficheiros, classes, funções,
variáveis de ambiente e tabelas são ingleses. Fica em português apenas o **conteúdo**: as
mensagens que o operador lê, os rótulos do relatório, os textos da interface e a documentação
— comentários incluídos. Nomes próprios não se traduzem: `SIMO`, `Banka`, `POS`, `eTicket`,
`MZN`.

As **rotas** são a excepção herdada: `/pos/validacao-credito-fecho` mantém os segmentos em
português do MozaOps v1, porque é o contrato que o frontend já consome.

## Aviso

Os ficheiros `.xlsx` do departamento são **dados bancários reais** e estão excluídos do
controlo de versões (`.gitignore`). Não os commitar, em circunstância nenhuma.
