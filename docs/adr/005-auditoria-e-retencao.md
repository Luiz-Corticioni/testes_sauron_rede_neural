# 005 — HMAC, âncoras e retenção

Novos elos usam HMAC-SHA256 v2 com SAURON_AUDIT_HMAC_KEY. Legados continuam v1:
não há como lhes dar autenticidade retroativa. A chave é obrigatória em produção,
deve ficar fora do banco/backups compartilhados e ser preservada para verificação.
Triggers SQLite impedem UPDATE/DELETE, inclusive via QuerySet. Administrador do
arquivo do banco ainda pode remover triggers: teste adversarial faz isso de propósito.
Âncoras assinadas detectam truncamento se uma cópia confiável sobreviver. O arquivo
é append-only pela aplicação; por padrão fica no volume de dados para funcionar
com container read-only. Configure destino externo, permissões e coletor/syslog externo.
Quem controla ao mesmo tempo aplicação, chave e coletor pode forjar a trilha.
Syslog usa HOST:PORT e deve estar em rede protegida/encaminhador TLS.

Política inicial: conservar trilha online por 365 dias no mínimo; arquivar segmentos
mensalmente por `arquivar_auditoria --ate-id ID --saida DESTINO`. O comando exporta e
ancora antes de registrar o arquivamento, e preserva a cadeia online. Não executa
DELETE; expurgo físico exige procedimento operacional separado, revisão de retenção,
restauração ensaiada e preservação dos elos/âncoras. Prazo deve ser aprovado pela
organização conforme suas obrigações; não é prescrição legal.

