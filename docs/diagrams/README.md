# Diagramas

Diagramas de origem da arquitetura, vindos da apresentação inicial. Os diagramas **vivos** —
os que devem ser mantidos e consultados — estão em Mermaid dentro de
[`../../ARCHITECTURE.md`](../../ARCHITECTURE.md), porque renderizam no Bitbucket e evoluem em
diff com o código. Estes PNG ficam como registo do ponto de partida.

| Ficheiro | Conteúdo | Estado |
|---|---|---|
| `arquitetura.png` | Vista geral: Browser → OSB → serviços → Postgres/RabbitMQ/observabilidade | Válido |
| `camadas_microservice.png` | Camadas dentro de um contentor | ⚠️ Ver nota |

## ⚠️ Nota sobre `camadas_microservice.png`

O diagrama mostra `services → domain → repositories`, o que faz o **domínio depender para
baixo**. Se e quando um serviço ganhar `domain/`, a dependência deve ser **invertida** — o
domínio define as interfaces (*ports*) e a infraestrutura implementa-as. O diagrama deve ser
corrigido nessa altura.

O diagrama mostra também `domain/` como camada obrigatória de todos os serviços. Isso já não é
o desenho vigente: ver [ADR 0003](../adr/0003-estrutura-enxuta-em-vez-de-hexagonal.md).
