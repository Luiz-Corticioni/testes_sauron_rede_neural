# Histórico de alterações

## Não lançado — Sprint 5

- API v1: seleção incremental para páginas ordenadas por risco; ausência de um resultado deixa de ser tratada como risco zero. O cálculo global do modelo mantém seus custos e limitações.
- Medição reproduzível do modelo matemático em grafos sintéticos de 10 mil e 100 mil ativos, com pico de memória do processo e limitações documentadas.
- Decisão de licença registrada como pendente, sem selecionar uma licença pelo responsável.

- Sensores de isca, importação manual de eventos minimizados e alertas agrupados; sem coletor nem exposição de rede.

- Senhas novas usam Argon2id; hashes legados compatíveis são atualizados após verificação.
- API v1 de leitura para ativos e incidências por vulnerabilidade, com permissões, MFA, paginação e contrato OpenAPI. A API de escrita permanece pendente.
- Consulta local interativa da API e verificações mypy/OpenAPI na CI.
- Identificação opcional dos recursos Docker para a matrícula da faculdade.
- Atualização da imagem base e correção da exposição de detalhes internos de integridade. A aprovação do scan e a implantação real dependem da execução.
- [Relatório de rastreabilidade e limitações](docs/SPRINT5_RASTREABILIDADE.md).

Este arquivo não cria uma release nem atribui uma versão semântica retroativamente.
