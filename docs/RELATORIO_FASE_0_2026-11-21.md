# Fase 0 — credenciais e validação PostgreSQL — 21/11/2026

Este relatório complementa o [registro anterior](RELATORIO_FASE_0_2026-11-20.md).
A fase permanece aberta: falta a medição ponta a ponta do cálculo de risco com
banco e HTTP em 10 mil e 100 mil ativos; a implantação
real e o CI da branch não foram verificados.

O responsável escolheu a Apache 2.0 para o código próprio; a
[decisão e os limites da verificação](DECISAO_LICENCA.md) foram registrados.

## Mudanças

- A suíte PostgreSQL de relações e cobertura foi adaptada: dois testes que
  dependem do `TestCase` do Django são substituídos naquele backend por cenário
  em `TransactionTestCase`. Esse cenário confere exportação e restauração de
  relação com autoria e evidência, membros e revisão de cobertura. Isso permite
  que o backup inicie `REPEATABLE READ` antes das consultas.
- A API recebeu credenciais de integração para leitura, com escopos, segredo
  aleatório exibido uma vez, hash armazenado, expiração, rotação, revogação,
  limites e trilha de auditoria. Emissão e gestão exigem superusuário, sessão,
  MFA, reautenticação recente e CSRF. O token não autoriza operações humanas ou
  administrativas. A [ADR 014](adr/014-credenciais-integracao.md) registra a
  decisão e o [guia](CREDENCIAIS_INTEGRACAO.md) explica o uso e as limitações.
- Credenciais e limites foram excluídos dos backups e exportações para evitar
  que uma restauração reative um token revogado. Após restauração, emita novos.
  As migrações `0040` e `0041` criam as tabelas de credenciais e limite de origem.

## Verificações executadas

- PostgreSQL 16 descartável: `manage.py test tests.test_postgres_concorrencia
  tests.test_credenciais_api tests.test_api_v1_sprint5
  tests.test_relacoes_tipadas tests.test_cobertura_evidencias --noinput`:
  95 testes, sucesso, três exclusões `TestCase` com testes equivalentes em
  `TransactionTestCase`. Inclui oito acessos concorrentes com limite de quatro.
- SQLite/Windows: 553 testes executados com sucesso, quatro exclusivos de
  PostgreSQL pulados.
- Imagem Linux, rede desativada: 552 testes executados com sucesso, quatro
  exclusivos de PostgreSQL pulados. O artefato com credenciais foi varrido por
  Trivy 0.76.2: nenhum achado HIGH/CRITICAL identificado na base usada.
- Ruff, Bandit, mypy no escopo existente, validação OpenAPI, verificação de
  migrações e seis testes pytest passaram. Bandit apresentou aviso sobre uma
  anotação `nosec` preexistente no subprocesso de restauração.

## Limitações

Os ensaios PostgreSQL usaram conexão sem TLS somente em loopback, banco
descartável e driver instalado em diretório de testes. O backup originado no
PostgreSQL foi restaurado para SQLite; restauração para PostgreSQL não foi
implementada nem validada. O limite de tokens grava no banco a cada consulta;
sua capacidade sob carga ainda não foi medida. A ausência de achados do scanner
não prova ausência de vulnerabilidades. Nenhuma destas verificações comprova a
configuração de uma implantação pública.
