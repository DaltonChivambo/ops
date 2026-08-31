# Clientes e Contas

Departamento reservado — ainda sem automação construída. Pasta criada agora
para não obrigar a decidir a estrutura mais tarde, mas **vazia de propósito**:
a regra do catálogo (`core/navigation.ts`) é que só entra o que existe, e o
mesmo vale para a barra lateral (`layout/sidebar.ts`) — não aparece lá até ter
a primeira automação.

## Quando a primeira automação deste departamento chegar

1. Criar a pasta da ilha aqui dentro (`features/customers-and-accounts/<ilha>/`),
   pelo mesmo padrão de `features/payments-and-channels/`.
2. Acrescentar `'customers-and-accounts'` a `DepartmentId` e uma entrada a
   `DEPARTMENTS`, em `core/navigation.ts`.
3. Acrescentar o grupo à barra lateral, em `layout/sidebar.ts`.
