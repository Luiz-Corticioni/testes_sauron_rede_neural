# Remediação Sauron

Todos os testes usam banco/arquivos temporários. Commits por item; branches fix/p0, fix/p1 e feat/p2-base são checkpoints sequenciais.

ID | status | commit | testes | desvios/decisões
---|---|---|---|---
R1 | concluído | `4b0875c` | tests.test_remediacao_imune.R1 (vermelho→verde) | Afinidade sem decaimento; arquivamento e prioridade persistida.
R2 | concluído | `83609d0` | tests.test_remediacao_imune.R2 (vermelho→verde) | Só ativos contam; evicção arquiva, não apaga.
R3 | concluído | `58631ca` | tests.test_remediacao_imune.R3 (vermelho→verde) | ADR 001: componente ambíguo não é escolhido por ordem.
R4 | concluído | `d4bcf96` | tests.test_remediacao_dominio.R4 (vermelho→verde) | Versão e produto são guardas; força só ordena. Compatibilidade de perfis legados preservada.
R5 | concluído | `8d9c7f6` | tests.test_remediacao_imune.R5 (vermelho→verde) | Autoria e instante persistem e coincidem com auditoria.
R6 | concluído | `0245efa` / `4faffdc` | tests.test_remediacao_imune.R6 (vermelho→verde) | Permissão Gerentes, evidência e proveniência do descarte. Legado sem evidência revogado.
R7 | concluído | `266026e` / `4faffdc` | tests.test_remediacao_operacao.R7 (vermelho→verde) | ADR 002: decisão pendente mantém TRATAMENTO, sem suprimir risco.
R8 | concluído | `f36ab77` | tests.test_remediacao_seguranca.R8 (vermelho→verde) | Pares 5, IP 20 nomes distintos, usuário global apenas alerta/atraso. CIDRs explícitos.
R9 | concluído | `2b53971` | tests.test_remediacao_transacoes.R9 (vermelho→verde) | Fila de on_commit deduplica e respeita rollback; exportação só explícita.
R10 | concluído | `32142ad` | tests.test_remediacao_nvd.R10 (vermelho→verde) | CVSS v4 informado, não recalculado; limite por CPE e retries limitados.
R11 | concluído | `51db867` | tests.test_remediacao_operacao.R11 (vermelho→verde) | Supressão configurável por tipo/ativo/chave, padrão 7 dias.
R12 | concluído | `03dc751` | 55 testes, FIRST exaustivo, payloads, grupos, checks e Bandit | CI/SBOM/Trivy configurados; Docker não executado. TODO SHAs + Dependabot. Pip-audit remoto não concluiu.
R13 | concluído | `9acd790` | tests.test_matching.R13 (vermelho→verde) | ADR 003; fixture sintética; AND/negação permanece hipótese.
R14 | concluído | `901f877` | tests.test_risco_esparso.R14 (vermelho→verde), golden existente | ADR 004: materialização da API densa fora da meta do núcleo.
R15 | concluído | `a65f53d` | tests.test_auditoria_adversarial.R15 (vermelho→verde) | ADR 005: retenção exporta/ancora sem excluir originais; proteção externa depende do coletor.
R16 | concluído | `3de45be` | tests.test_mfa.R16 (vermelho→verde), token real/replay | ADR 006: provisionamento local, recuperação administrativa, reauth mais estrita em POSTs.
R17 | concluído com pré-requisito | `0388bae` / `d2b4c45` | tests.test_backup.R17 e test_preparacao_banco (vermelho→verde), restauração limpa SQLite | ADR 007: PostgreSQL exige driver externo à lista autorizada; não executado localmente.
R18 | concluído | `979bb90` | tests.test_heartbeat.R18 (vermelho→verde) | Processos separados, inicialização independente; heartbeat indica conclusão, inclusive parcial.
R19 | concluído | `b707d5b` | tests.test_saude.R19 (vermelho→verde) | Liveness interceptada antes de sessão/ORM; limite em memória por processo.
Extras F1 | concluído | R20–R24 | M-2/M-4/M-5/M-6/I-10 | Detalhes nas linhas abaixo.
Base F2/3 | concluído | R26–R30 | quatro módulos puros + ADRs 009–012 | Sem integração à produção.
M-4 | concluído | `c81dc9f` | tests.test_series_degrau.M4 (vermelho→verde) | Snapshots por execução da rotina; área ZOH e regressão mínima 24 h.
M-5 | concluído | `b538477` | tests.test_edo.M5 e payloads FIRST/Euler (vermelho→verde) | AST direta; Euler explícito e RK4 são EDO, Simpson/trapézios são quadratura.
M-6 | concluído | `9194263` | tests.test_cvss_ambiental.M6 e 2592 vetores base (vermelho→verde) | Ambiental ordena prioridade e SLA; risco puro mantém unidade/base. 3.0/v4 preservam score da fonte.
I-10 | concluído | `41b55f5` | tests.test_ciclo_snapshot.I10 e imune (vermelho→verde) | Snapshot otimista validado pela cabeça auditada; lote rotativo e aprendizagem limitada.
M-2 | concluído | `77ea6b5` | tests.test_politica_pesos.M2 (vermelho→verde) | ADR 008: noisy-OR só laboratório; produção recusa ativação nesta rodada.
F2/3 noisy-OR | concluído | `8e63177` | tests.test_noisy_or (vermelho→verde) | Ponto fixo monótono esparso; comparação linear apenas para probabilidades pequenas.
F2/3 contágio | concluído | `8327625` | tests.test_contagio (vermelho→verde) | SIS/SIR Euler/RK4, MTTR de histórico e cenário por vulnerabilidade; sem calibração operacional.
F2/3 caminhos | concluído | `3b34266` | tests.test_caminhos_ataque (vermelho→verde) | Zonas/portas exigem regras explícitas; sem scan ou afirmação de exploração.
F2/3 previsão | concluído | `278cb3d` | tests.test_previsao (vermelho→verde) | Brier, calibração e PR-AUC trapezoidal, walk-forward sem rótulo futuro no callback.
Revisão final | concluído | `4faffdc` | tests.test_formularios_seguros (vermelho→verde) | Formulários/Admin preparam solicitação pendente; autorização de alocação exige autor corrente.

## Portão da Fase 0 — 27/10/2026

- check: sem problemas.
- makemigrations --check: sem alterações.
- migrate: banco limpo temporário, todas as migrações aplicadas.
- test: 55 testes passaram, incluindo 2.592 subcasos CVSS e 34 payloads Euler.
- ruff check .: passou.
- check --deploy --fail-level WARNING: passou em produção simulada.
- Bandit: passou; supressões locais justificadas em VALIDACAO.md.
- pip-audit/geração de hashes: serviço remoto não retornou dentro da execução local;
  comandos e CI preparados. Não há alegação de auditoria de dependências concluída.






## Portão da Fase 1 — 27/10/2026

check, makemigrations --check, 83 testes, Ruff e check --deploy com nível WARNING
passaram. Migrações aplicadas em banco limpo, revertidas até 0010 e reaplicadas.
Bandit passou, com exclusões locais B310 (HTTPS/hosts) e B404/B603 (subprocessos
locais fixos de restauração). Benchmark esparso medido entre 10 e 35 ms no cenário
documentado; a meta não inclui materialização densa da API.
Não houve execução local de PostgreSQL, Docker, Trivy ou validação externa de dados.





## Pendências de implantação e riscos residuais

- PostgreSQL: parser/isolamento por vendor e compose opcional entregues; driver
  precisa vir em imagem externa para respeitar a lista de dependências permitidas.
  Backend/backup de PostgreSQL não foi exercitado contra servidor real.
- Docker e Trivy não estão disponíveis localmente; pipeline foi configurado,
  mas construção/scan de imagem precisam executar no CI.
- pip-audit remoto e geração de lock com hashes não concluíram localmente.
  requirements.in e comandos reproduzíveis estão entregues; pins atuais não são
  apresentados como lock completo/auditoria de vulnerabilidades aprovada.
- Pin de actions por SHA aguarda hashes verificados; TODO explícito + Dependabot.
- V1 não ganha autenticidade retroativa; âncoras requerem coletor/cópia externa e
  chaves protegidas. Criptografia de disco do banco operacional é responsabilidade
  de implantação; Fernet protege as cópias de backup.
- Fixtures de matching e cenários matemáticos são sintéticos e não calibrados.
  Nenhuma integração externa nova/ação SOAR/teste ofensivo foi ativada.

## Validação final da entrega

A suíte final passou com 97 testes, incluindo 2592 vetores base CVSS, 128 casos
ambientais, payloads AST e restauração cifrada com verificação da auditoria.
check, makemigrations --check, Ruff, Bandit e check --deploy com fail-level WARNING
passaram. YAML de compose/CI/Dependabot foi lido com parser.
Evidência: docs/evidencias/VALIDACAO_FINAL.txt. Respostas 403/503 exercitadas em testes
e aviso de staticfiles ausente no ambiente de testes são esperados; o deploy check
simulado terminou sem avisos. Nenhuma validação externa pendente é dada como passada.

A revisão final também versiona o cache pelos fatores configurados (teste vermelho→verde) e mantém âncora padrão no volume gravável, exigindo cópia externa para resistência ao adversário.


## Revisão funcional e Linux — 27/10/2026

Revisão adicional em `revisao/linux-funcional`. Relatório e limites em
[REVISAO_CRITICA.md](REVISAO_CRITICA.md); guia em [INSTALACAO_LINUX.md](INSTALACAO_LINUX.md).
123 testes aprovados, validações estáticas/deploy aprovadas e auditoria de dependências
sem vulnerabilidades conhecidas na consulta realizada. Execução Linux real e documento
adicional de requisitos mínimos permanecem pendentes.

ID | commit | alteração
---|---|---
RC01 | `7705a4a` | decisões segregadas e fila de revisão
RC02 | `dd51d39` | reforçar MFA e confiança no protocolo do proxy
RC03 | `36e149a` | publicar restauração apenas após validação
RC04 | `335f94c` | exigir âncoras em produção e rejeitar adulterações
RC05 | `3fc20d2` | tratar entradas vazias e conflitos no cadastro web
RC06 | `4f34f48` | exportar cadastros completos com controle de auditoria
RC07 | `e04692b` | corrigir cobertura de componentes e reaprendizagem
RC08 | `b60e240` | automatizar instalação Fedora e RHEL com atualização protegida
RC09 | `7266844` | preservar matrizes esparsas na API e apresentação
RC10 | `fc5456a` | corrigir indicador público de disponibilidade e título de salas


## Comparação CVSS e orientação — 27/10/2026

Branch `feat/comparacao-cvss`, a partir de `083644c`. Escopo e evidências em
[COMPARACAO_CVSS.md](COMPARACAO_CVSS.md).

ID | situação | commit | evidência / decisão
---|---|---|---
CV01 | implementado | `a27b5c2` | conferir cálculos e corrigir limites numéricos
CV02 | implementado | `65dbd3c` | comparar CVSS 3.1 e 4.0 da NVD e orientar stakeholders

151 testes aprovados; 2.592 vetores base 3.1, 2.000 vetores ambientais/temporais
novos, 50 grafos em dois perfis e oráculos analíticos. Validações de lint, segurança,
JavaScript e deploy simuladas aprovadas. NVD 4.0 é nota externa com estrutura e
proveniência verificadas, sem algoritmo local 4.0. Comparação não modifica o banco.
A auditoria de notas registra divergências e notas sem vetor para revisão humana.
