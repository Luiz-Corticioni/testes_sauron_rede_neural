# Melhorias da curadoria — 15/11/2026

[Curadoria e roadmap](curadoria/00-resumo-executivo.md) · [Documentação](README.md)

## Q1 — Cenário demonstrativo operacional

O comando `seed_demo --operacional` falhava porque tentava atribuir autoria a um aceite fora do contexto de usuário e criar um aceite já vencido, incompatível com as regras atuais. O teste reproduziu a falha antes da correção.

A demonstração agora usa dois usuários fictícios sem senha utilizável e os serviços de solicitação e aprovação existentes. O aceite é válido por 15 dias, com solicitante e aprovador distintos; o prazo de outra incidência continua vencido para demonstrar acompanhamento. Isso mantém as validações de autorização e segregação, em vez de forçar registros inválidos. A série, a justificativa e o alerta continuam identificados como simulação.

Testes em banco isolado verificaram execução, idempotência, proteção de base existente, autorização segregada e rollback/auditoria após erro simulado: oito testes de cenário e decisões passaram. Não aplique o seed sobre inventário real; o comando não substitui validação em produção.
