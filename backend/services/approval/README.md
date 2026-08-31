# Approval / Workflow

Bounded context **Approval / Workflow**. Cobre: pedidos de aprovação — compra, acesso, mudança. Genérico e reutilizado pelos outros contextos: recebe `tipo_de_pedido` e um payload opaco, devolve aprovado ou rejeitado. No dia em que tiver um `if tipo == "compra_de_ativo"`, deixou de ser genérico.

## Perfil

HTTP + publisher — ver `ARCHITECTURE.md` §3.1.

Um serviço, um schema, uma pasta (ADR 0004). Se este contexto vier a precisar de um segundo
processo deployável, é uma decisão de arquitetura nova, não uma extensão silenciosa desta pasta.
