# 009 — Ingestão futura de telemetria
Status: proposta; nenhuma integração externa implementada nesta rodada.

Adaptadores futuros Wazuh/osquery devem publicar eventos normalizados em contrato
versionado, com ID idempotente, asset_id resolvido, observed_at/received_at em UTC,
origem, confiança, evidência e classificação de dados. ECS e OCSF são candidatos
a mapeamento; manter tabela explícita e campos originais em armazenamento restrito.
Mapeamento ATT&CK deve registrar técnica, versão e justificativa, sem tratar um
indicador isolado como ataque comprovado.

Validar schema, tamanho, cardinalidade, relógio e autenticação do produtor; fila
com limite, backpressure e quarentena de eventos inválidos. Não executar comandos
recebidos em payload. Separar permissão de publicar da de aprovar regras.
Começar por replay de fixtures anonimizadas; medir perda, atraso, duplicação,
precisão e falsos positivos antes de qualquer integração operacional.

