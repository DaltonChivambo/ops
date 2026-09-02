# Diagramas

Diagramas de origem da arquitetura, vindos da apresentação inicial. Os diagramas **vivos** —
os que devem ser mantidos e consultados — estão em Mermaid dentro de
[`../../ARCHITECTURE.md`](../../ARCHITECTURE.md), porque renderizam no Bitbucket e evoluem em
diff com o código. Estes PNG ficam como registo do ponto de partida.

| Ficheiro | Conteúdo | Estado |
|---|---|---|
| `arquitetura.png` | Vista geral: Browser → OSB → serviços → Postgres/RabbitMQ/observabilidade | Válido |
| `camadas_microservice.png` | Camadas dentro de um contentor | Válido — ver nota |

## Nota sobre `camadas_microservice.png`

O diagrama mostra `controllers → services → (domain/ + infrastructure/) → repositories`, e é
**essencialmente o desenho vigente**: a [ADR 0008](../adr/0008-cinco-camadas-por-servico.md)
adoptou estas cinco camadas, com os nomes que aqui estão.

Duas diferenças, ambas deliberadas:

**A dependência não foi invertida.** O diagrama põe `services → domain → repositories`, o que
faz o domínio depender para baixo. A [ADR 0003](../adr/0003-estrutura-enxuta-em-vez-de-hexagonal.md)
e esta nota diziam que, no dia em que houvesse `domain/`, o domínio devia passar a definir as
interfaces e a infraestrutura a implementá-las. Há `domain/`, e decidiu-se **não** inverter: há
um adaptador por repositório e nenhum segundo candidato, portanto o *port* seria uma interface
escrita para um implementador só. O gatilho está registado na 0008 — entra quando existir o
segundo adaptador. Na prática o domínio não depende de ninguém: são os serviços e os
repositórios que dependem dele.

**`repositories/` é camada irmã e não filha da infraestrutura.** Como no diagrama. A
infraestrutura fica com a sessão, as tabelas e os adaptadores de ficheiros.

O diagrama fica, portanto, válido como desenho de partida — o que não vale é a seta que sai do
`domain/`.
