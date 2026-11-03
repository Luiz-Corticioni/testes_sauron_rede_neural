# 011 — SOAR-lite e freio por blast radius
Status: proposta; nenhuma ação externa implementada.

Primeiras ações candidatas: abrir tarefa, aumentar coleta por prazo e sugerir regra
temporária com expiração. Cada adaptador deve ter precondição, dry-run, idempotência,
plano de compensação, timeout, autorização e trilha HMAC antes/depois.
Execução deve exigir operador e aprovação separada em mudanças de maior alcance.
Falhas/estados desconhecidos interrompem o plano; não repetir cegamente.

Antes de isolar nó, percorrer dependentes transitivos e sua criticidade.
Regra de segurança: NUNCA isolar automaticamente nó com três ou mais dependentes
críticos (limite proposto, podendo ser ainda mais restritivo); ciclos e grafo
incompleto também bloqueiam automação. Mostrar impacto estimado e alternativas.
Isolamento deve ser manual até evidência em laboratório, limites aprovados e
restauração ensaiada. Um botão de desfazer sem compensação testada não é reversibilidade.

