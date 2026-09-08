# 0010 — Acesso por área, sem papéis

- **Estado**: Aceite
- **Data**: 2026-09-08
- **Decisor(es)**: Dalton Chivambo

## Contexto

O primeiro desenho da autorização tinha três papéis — `operator`, `supervisor` e
`auditor` — atribuídos pelo departamento e pela função registados no GEEA. O
`supervisor` trazia o `operator` atrás, e havia um acto reservado: marcar um caso
como regularizado.

A separação não corresponde a nada no DOP. Quem opera, quem supervisiona e quem
chefia o departamento fazem, hoje, exactamente o mesmo trabalho dentro do sistema:
correm a validação, olham para as divergências, regularizam os casos que ficam
apurados. A hierarquia existe na sala; não existe na aplicação. Manter três níveis
era manter uma regra que ninguém tinha pedido, com o custo de que a primeira pessoa
a ser bloqueada por ela ia ter razão em queixar-se.

O que **é** verdade é a fronteira entre áreas: a validação de crédito de fechos de
POS é dos Meios de Pagamentos e Canais, e não é do banco todo.

Uma nota de vocabulário, porque é onde isto se confunde — e onde a primeira versão
deste ADR ainda errava. O GEEA manda a unidade orgânica da pessoa numa claim
chamada `departmentCode` — mas o ficheiro de unidades tem 227 entradas e só 18
são departamentos: o resto são áreas, serviços, gabinetes, direcções e unidades
de negócio. «Meios de Pagamentos e Canais», o rótulo que a barra lateral mostra,
**é o departamento** (o Departamento de Apoio Operacional, código `2350`) — não
uma área. Dentro dele há unidades reais e distintas: `CANAIS E SERVIÇOS DE
INTEGRAÇÃO` (código `3230`) e `SERVIÇO DE MEIOS DE PAGAMENTO` (código `2442`) são
duas, cada uma com o seu código, a sua chefia e a sua equipa. Tratar o
departamento inteiro como se fosse uma área única dava acesso à validação de
fechos de POS a qualquer pessoa do departamento — incluindo quem está em Meios de
Pagamento e nunca lidou com um POS.

## Decisão

**A unidade de acesso do MozaOps é a área.** Não há papéis.

- Cada automação pertence a uma área — hoje `canais` (unidade `3230`, «Canais e
  Serviços de Integração»), a de quem trata do POS/ATM/Quiosques — declarada no
  `service.yaml` e no catálogo do frontend. A área é a unidade orgânica real que
  faz o trabalho, não o departamento que a contém: «Meios de Pagamentos e
  Canais» continua a existir como rótulo da barra lateral, mas não abre nada
  sozinho — quem abre é a área lá dentro.
- Cada pessoa tem zero ou mais áreas, decididas pelo backend a partir da unidade
  orgânica que o GEEA manda — o mapa está em `AUTH_AREAS`, na forma
  `area:unidade,unidade`. Uma área corresponde a mais do que uma unidade, porque
  o organigrama não coincide com o que o DOP trata como uma equipa.
- Quem é da área faz **tudo** o que a automação faz. A guarda é uma só, no router
  inteiro do serviço, e não rota a rota.
- Não há área por omissão. Quem não corresponder autentica-se e cai em «sem acesso».
- **O vocabulário fixa-se**: no nosso código, `area` é a área do MozaOps;
  `department`/`departmentCode` são as claims do GEEA e guardam o nome de quem as
  emite. Um `Principal` tem os dois, e não são a mesma coisa.

Módulos sem área — hoje só o Dashboard — são transversais: basta ter sessão.

## Consequências

- **Menos código e menos configuração.** Saem o `Role`, o `RoleMapping`, as cinco
  variáveis de ambiente de papéis, o `canExecute`/`canResolve` do SPA e as guardas
  `require_writer`/`require_resolver`. Fica um mapa e uma guarda.
- **Regularizar um caso deixa de ser reservado.** É o acto com mais significado do
  sistema — a data vai para o relatório do departamento — e passa a poder ser feito
  por qualquer pessoa da área. É deliberado, e é a parte que fica pior: a
  reversibilidade está na trilha de auditoria (quem regularizou e quando), não no
  controlo de acesso.
- **Uma automação de outra área nasce fechada.** Basta declarar a área dela; nada
  no código da autenticação muda. Inclui uma automação de «Meios de Pagamento»
  (`2442`) — fica fechada à área `canais`, mesmo estando no mesmo departamento.
- **Voltar a ter papéis é trabalho de uma tarde**, e este ADR fica a dizer porque é
  que não os há. O sítio onde nasceriam é o `require_area` do `dependencies.py`.

## Alternativas consideradas

**Manter os papéis colapsados num só (`member`).** Menos código a apagar hoje.
Rejeitado: mantinha um vocabulário que não corresponde a nada, e o ecrã de erro
continuava a falar de «papel actual» a quem o que falta é ser da área.

**Gatilho só à entrada da plataforma — quem é de uma unidade autorizada vê tudo.**
Mais simples ainda. Rejeitado porque a primeira automação de outro departamento
obrigava a voltar aqui, e porque «vê tudo» inclui os números de fecho de um canal
que não é o seu.

**Manter a hierarquia à espera de que o DOP a queira.** Rejeitado: é escrever hoje
uma regra para um requisito hipotético, e pagá-la todos os dias em configuração,
testes e explicações a quem chega.

**Área ao nível do departamento, em vez da unidade real.** Foi a primeira versão
deste ADR: uma área só (`payments-and-channels`, mapeada ao código `2350` do
departamento) a cobrir POS, ATM, Quiosques, Pagamentos e Fraudes de uma vez.
Mais simples de configurar — uma entrada no `AUTH_AREAS`, não uma por unidade —
mas errada: dava acesso à validação de fechos de POS a qualquer pessoa do
departamento, incluindo quem está em Meios de Pagamento e nunca tratou de um
POS. Rejeitado a favor de mapear à unidade real (`canais`, `3230`), que é o que
o organigrama já distingue. O custo é uma entrada no `AUTH_AREAS` por unidade
em vez de uma por departamento — pago uma vez, na configuração.
