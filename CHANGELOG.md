# Histórico de alterações

## Não lançado — Sprint 5

- Remediação: comparação revisável de scans Trivy, chamados Jira/GLPI opcionais e emissão OpenVEX validada; backup compatível com migrações anteriores.
- Observações offline versionadas, desativadas por padrão, com prévia, importação atômica e revisão humana; perfis restritos para scanners, GLPI e regras de rede.
- Backtest offline de cinco estratégias em snapshots históricos, com limites temporais, métricas e intervalos ilustrativos; fixture sintética separada de dados reais.
- Monte Carlo v2: fatores declarados, caminhos, causa comum, apetite, intervenções, sensibilidade e ajuste heurístico opcional por perdas registradas.
- Prioridades explicam parcelas direta e propagada; snapshots novos registram top 10, backlog vencido e MTTR para comparação histórica autorizada.
- Fontes: histórico sanitizado de tentativas KEV e resumo de atualidade, idade e lacunas; importações de scanner visíveis somente com permissão.
- Índice de completude de evidências por ativo e serviço; simulação informa cobertura EPSS e componentes financeiros indeterminados, sem alterar o risco.

- API v1: seleção incremental para páginas ordenadas por risco; ausência de um resultado deixa de ser tratada como risco zero. O cálculo global do modelo mantém seus custos e limitações.
- Medição reproduzível do modelo matemático em grafos sintéticos de 10 mil e 100 mil ativos, com pico de memória do processo e limitações documentadas.
- Backup PostgreSQL chamado dentro de transação existente é recusado com mensagem explícita para preservar o isolamento necessário; concorrência da auditoria verificada em banco temporário.
- Credenciais de integração de leitura com escopos, expiração, rotação, revogação, limites por credencial e origem e auditoria; emissão exige superusuário com sessão, MFA, reautenticação e CSRF.
- Licença Apache 2.0 escolhida pelo responsável para o código próprio; avisos de componentes de terceiros preservados.

- Sensores de isca, importação manual de eventos minimizados e alertas agrupados; sem coletor nem exposição de rede.

- Senhas novas usam Argon2id; hashes legados compatíveis são atualizados após verificação.
- API v1 de leitura para ativos e incidências por vulnerabilidade, com permissões, MFA, paginação e contrato OpenAPI. A API de escrita permanece pendente.
- Consulta local interativa da API e verificações mypy/OpenAPI na CI.
- Identificação opcional dos recursos Docker para a matrícula da faculdade.
- Atualização da imagem base e correção da exposição de detalhes internos de integridade. A aprovação do scan e a implantação real dependem da execução.
- [Relatório de rastreabilidade e limitações](docs/SPRINT5_RASTREABILIDADE.md).

Este arquivo não cria uma release nem atribui uma versão semântica retroativamente.
