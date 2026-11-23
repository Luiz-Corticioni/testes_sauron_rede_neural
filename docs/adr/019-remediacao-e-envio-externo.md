# ADR 019 — Remediação com evidência e efeitos externos explícitos

Status: implementado com limitações; 22/11/2026.

## Contexto

Uma CVE ausente de um scan não comprova correção, e a criação de chamados em
outros sistemas não participa da transação do banco do Sauron. Um timeout pode
ocorrer depois de o destino aceitar a criação. Repetições automáticas podem criar
chamados duplicados, inclusive quando o primeiro resultado for desconhecido.

## Decisão

1. Comparar uma observação Trivy revisada com outro relatório do mesmo alvo,
   fonte e versão declaradas; registrar sugestão sem alterar a incidência.
2. Preservar o fluxo de decisões, permissões, prazo e aprovação existente.
3. Manter adaptadores externos desativados por padrão. Após autorização e
   confirmação explícita, gravar e auditar `ENVIANDO` antes da chamada; registrar
   `CRIADO` ou `INCERTO` em outra transação. Não reenviar automaticamente.
4. Emitir inicialmente apenas OpenVEX `fixed` com CVE, produto exato e evidência
   de decisão concluída. Validar contra esquema oficial local e auditar o hash.

## Consequências

A transação não pode assegurar entrega exatamente uma vez entre bancos e serviços
independentes. Falha de processo ou do banco pode deixar o estado em `ENVIANDO`;
`INCERTO` inclui falhas anteriores ou posteriores à criação. A solução privilegia
evitar duplicatas e requer consulta e reconciliação manual no destino. Uma única
tentativa por incidência/provedor limita ciclos futuros. O adaptador GLPI exige
token de sessão já criado e não o renova. Sem homologação real, a compatibilidade
com configurações específicas de Jira e GLPI é desconhecida.

O esquema OpenVEX não valida o mérito, a autoria real ou o sigilo da evidência.
A comparação também depende de afirmações do operador sobre escopo e origem. Não
se traduzem aceites, mitigações ou simulações em correções comprovadas.
