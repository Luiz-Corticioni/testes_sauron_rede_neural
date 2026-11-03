# 002 — Decisões humanas segregadas

Aceites de alta severidade e encerramentos de CVSS >= 7/KEV aguardam segundo usuário.
Enquanto isso, status TRATAMENTO conserva o risco e o SLA; decisao_pendente mostra o
resultado solicitado. O segundo usuário repete a operação do status solicitado.
Aceite: primeiro precisa aceitar_risco, segundo aprovar_aceite_risco.
Correção/mitigação: ambos change_incidencia, com evidência obrigatória.
Campos de autoria vêm do contexto autenticado. QuerySet.update/bulk_create são APIs
privilegiadas de migração, não disponíveis em rotas humanas.
Admin deixa autores e exceções readonly; linha de base usa formulário dedicado com scan ou CLI.
Registros legados sem evidência/dupla aprovação voltam ao tratamento no backfill,
com cópia dos valores anteriores para reversão.
