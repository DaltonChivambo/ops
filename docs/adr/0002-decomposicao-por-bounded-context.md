# 0002 — Decomposição por bounded context

- **Estado**: Aceite
- **Data**: 2026-08-25
- **Decisores**: Dalton Chivambo

## Contexto

O pedido inicial descrevia microserviços "associados aos diversos departamentos da Direção de
Operações". Havia duas leituras possíveis, e ambas conduzem a arquiteturas más:

- **Um serviço por funcionalidade** (login, tickets, inventário, agendamento, aprovações,
  alertas, relatórios, notificações, importação Excel — nove serviços ou mais).
- **Um serviço por departamento**, seguindo o organigrama.

## Decisão

Decompor por **bounded context**, com o critério: *o que muda junto fica junto; o que tem ritmo
de mudança ou dono diferente, separa.*

Resultam **seis serviços**:

| Serviço | Responsabilidade |
|---|---|
| `auth` | login, permissões, roles; emite JWT (RS256) e expõe JWKS |
| `ticketing` | tickets, incidentes, atribuição |
| `asset` | inventário, ativos, licenças **e manutenção agendada** |
| `approval` | workflow de aprovação genérico, reutilizado pelos outros |
| `notification` | consome eventos → email/push |
| `reporting` | consome eventos → read model, relatórios e auditoria |

Duas coisas **não** são serviços:

- **Alertas de monitorização** — ficam no Grafana/Prometheus já existente; o alerting faz webhook
  para o Ticketing, que decide se abre incidente.
- **Importação/exportação Excel** — é infraestrutura (`infrastructure/files/excel/`) dentro de
  quem precisa dela, não um serviço.

O agendamento de manutenção fica dentro do `asset` porque manutenção é sobre o ativo e muda com
ele.

## Consequências

- Menos contentores, menos rede, menos superfície operacional do que a decomposição por
  funcionalidade.
- O `approval` e o `notification` são transversais a vários departamentos — o que confirma que o
  departamento não serve como eixo de decomposição
  (ver [0004](0004-pastas-planas-departamento-como-metadado.md)).
- **O risco de monólito distribuído não desaparece, muda de sítio.** Passa a estar nas relações
  entre os seis. Ficam três regras, verificáveis em `ARCHITECTURE.md` §3.3 e §8:
  1. Nada de chamada síncrona no caminho de leitura — o Ticketing guarda um snapshot do ativo
     recebido por evento, em vez de chamar o Asset a cada leitura.
  2. O Approval não pode conhecer os outros domínios — `tipo_de_pedido` + payload opaco. Um
     `if tipo == "compra_de_ativo"` significa que deixou de ser genérico.
  3. O Reporting é read-only e **eventualmente consistente** — constrói o seu próprio schema a
     partir de eventos e nunca lê os schemas dos outros. Tem de ser acordado com o negócio.
- O `notification` e o `reporting` existem para consumir eventos, o que torna o RabbitMQ e um
  entrypoint `worker.py` obrigatórios desde cedo — e não adiáveis como em
  [0003](0003-estrutura-enxuta-em-vez-de-hexagonal.md).

## Alternativas consideradas

**Um microserviço por funcionalidade.** Rejeitado: é o erro simétrico ao excesso de camadas —
fragmentação em nano-serviços, que troca chamadas de função por latência de rede e acopla os
serviços por chamadas síncronas em vez de por código. Produz exactamente o monólito distribuído
que a arquitetura de microserviços existe para evitar.

**Um microserviço por departamento.** Rejeitado por duas razões: cada serviço cresceria como um
mini-monólito com várias razões independentes para mudar, e o organigrama muda mais depressa que
o código — uma fusão de departamentos obrigaria a fundir serviços e bases de dados.
