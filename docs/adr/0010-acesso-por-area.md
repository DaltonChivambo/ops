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

Uma nota de vocabulário, porque é onde isto se confunde. O GEEA manda a unidade
orgânica da pessoa numa claim chamada `departmentCode` — mas o ficheiro de
unidades tem 227 entradas e só 18 são departamentos: o resto são áreas, serviços,
gabinetes, direcções e unidades de negócio. E o que o catálogo do MozaOps chama
«Meios de Pagamentos e Canais» é uma **área** do Departamento de Apoio Operacional,
não um departamento. Chamar «departamento» às duas coisas garantia que ninguém
percebia qual delas mandava.

## Decisão

**A unidade de acesso do MozaOps é a área.** Não há papéis.

- Cada automação pertence a uma área (`payments-and-channels`), declarada no
  `service.yaml` e no catálogo do frontend.
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
  no código da autenticação muda.
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
