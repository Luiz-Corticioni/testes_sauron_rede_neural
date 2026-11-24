# Roadmap e limitações do Sauron

Atualizado em 24/11/2026 na branch de correções. Este documento distingue código
presente de validação real; relatórios históricos preservam seus resultados de
teste e não certificam versões posteriores.

| Área | Estado e próximos passos |
|---|---|
| Fundamentos | Cadastro demonstrativo, paginação de risco, credenciais de leitura e licença Apache 2.0 existentes. Um ensaio WSGI com banco temporário e cálculo real foi realizado em 10 mil e 100 mil ativos; não mede TCP, TLS ou concorrência. Restauração para PostgreSQL não está implementada. |
| Qualidade | Há componentes por ativo, serviço, cenário e recortes principais de risco, com dados ausentes explícitos. Ainda faltam alguns laboratórios e registro de validação independente de premissas. |
| Priorização | A decomposição usa o cálculo real; EPSS, SSVC e criticidade do serviço não integram a fórmula atual. Uma política nova precisa explicar hipóteses e não atribuir probabilidades arbitrárias. |
| Monte Carlo v2 | Há fatores declarados, cenários, correlação e ajuste de custos. O ajuste é heurístico e exige revisão independente e dados locais representativos; a simulação não é previsão nem FAIR completo. |
| Backtest | A infraestrutura é reproduzível com dados sintéticos. Avaliação com dados históricos reais depende de arquivos obtidos e verificados pelo responsável; a fixture não comprova superioridade. |
| Observações offline | Há perfis delimitados e retenção configurável de 30 a 180 dias, com padrão de 90. Falta homologar arquivos reais e melhorar reconciliação; cópias em relações, auditoria e backups exigem controle próprio. |
| Remediação | Comparação Trivy e emissão OpenVEX cobrem recortes específicos. Jira e GLPI vêm desativados e foram testados com simulações; a homologação externa e reconciliação de envios incertos permanecem pendentes. |
| Visão executiva | O relatório usa registros existentes, com faixa de simulações e avisos de limitação. Precisa de avaliação com stakeholders e acessibilidade; não constitui certificação. |
| Entrega | O CI inclui SBOM como artefato, testes e análise de imagem, mas a execução da branch e publicação do artefato devem ser verificadas no GitHub. Implantação e validação no servidor exigem ambiente autorizado. O posicionamento e os avisos dos laboratórios foram atualizados nesta branch. |

## Limites dos laboratórios

Euler e contágio são modelos matemáticos exploratórios. O sistema imune produz
sugestões para revisão humana. O módulo de iscas registra e revisa eventos
importados: não instala honeypots públicos nem garante detecção de ataques.
Nenhum deles deve ser interpretado como prova de comprometimento.

## Evidências

Consulte os relatórios de [fundamentos](RELATORIO_FASE_0_2026-11-21.md),
[qualidade](RELATORIO_FASE_1_2026-11-21.md), [explicabilidade](RELATORIO_FASE_2_2026-11-21.md),
[Monte Carlo](RELATORIO_FASE_3_2026-11-21.md), [backtest](RELATORIO_BACKTEST.md),
[observações](RELATORIO_FASE_5_2026-11-22.md), [remediação](RELATORIO_FASE_6_2026-11-22.md)
e [visão executiva](RELATORIO_FASE_7_2026-11-24.md). O estado de um serviço
externo, dependência ou implantação pode mudar depois dessas verificações.
