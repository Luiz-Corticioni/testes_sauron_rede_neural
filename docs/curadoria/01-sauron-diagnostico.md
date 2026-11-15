# 01 — Diagnóstico do Sauron

[Resumo](00-resumo-executivo.md) · [Seleção](02-longlist-e-criterios.md) · [Roadmap](06-roadmap-recomendacoes.md)

**Base auditada:** checkout local `sprint5-conformidade`, commit `9774058` (14/11/2026); não se confunde com a branch `main`. Escopo: leitura orientada de modelos, serviços, segurança, deploy, testes e documentação, não auditoria integral de todas as linhas nem pentest. **FATO** designa evidência na base; **INFERÊNCIA** é julgamento técnico. A curadoria não alterou o código da aplicação nem executou código de repositórios externos.

## O que funciona no código

- **FATO — inventário e tratamento:** modelos [Ativo](../../inventario/models/ativos.py), [Vulnerabilidade](../../inventario/models/vulnerabilidades.py), [Incidencia](../../inventario/models/incidencias.py), [Software e Alerta](../../inventario/models/operacionais.py) e [serviços de cadastro](../../inventario/aplicacao/cadastros.py) representam ativos, falhas, associação, tratamento e alerta; [documentos/SBOM/VEX](../../inventario/aplicacao/documentos.py) acrescentam declarações e componentes. A associação não é prova automática de exploração.
- **FATO — contexto:** integrações [NVD/CISA KEV](../../inventario/infraestrutura/cve_client.py), [EPSS](../../inventario/aplicacao/epss.py) e [SSVC](../../inventario/aplicacao/ssvc.py); o estado e a atualização dependem de fontes externas. [Grafo de relações](../../inventario/dominio/grafo_relacoes.py) calcula alcance, não probabilidade de ataque.
- **FATO — risco:** [modelo matemático](../../inventario/matematica/risco.py) e [Monte Carlo 30 dias](../../inventario/aplicacao/montecarlo.py) utilizam entradas e limites explícitos. O [módulo financeiro](../../inventario/matematica/montecarlo.py) declara não implementar FAIR completo; `EPSS × fator de exposição` é hipótese de cenário, não uma probabilidade de comprometimento validada para o ativo. Sem EPSS observado e recente, o serviço sinaliza indisponibilidade.
- **FATO — iscas:** [modelo](../../inventario/models/honeypot.py), [serviço](../../inventario/aplicacao/honeypot.py) e [guia](../HONEYPOT_FASE1.md) aceitam manualmente lote JSON minimizado, deduplicam e agrupam alertas. Não iniciam servidor SSH, não fazem coleta automática nem ingerem diretamente formato Cowrie.
- **FATO — acesso e API:** Django 5.2 e dependências em [requirements](../../requirements.txt); formulários/views e serviços compartilham ORM. [API v1](../../inventario/web/api_v1.py) tem consultas e contrato [OpenAPI limitado](../openapi-v1.json); autentica por sessão/MFA e não oferece CRUD completo ou integração máquina-a-máquina documentada.

## Arquitetura, implantação e controles

- **FATO:** interface Django, domínio e serviços Python; SQLite por padrão; PostgreSQL opcional não validado no ambiente desta revisão ([settings](../../sauron_web/settings.py), [ADR 007](../adr/007-banco-backups.md)). O [Compose](../../compose.yaml) separa preparação, web e agendador, publica web em loopback, usa volume, filesystem somente leitura, retirada de capabilities e sem novos privilégios; [Caddy opcional](../../compose.https.yaml) não comprova HTTPS real.
- **FATO:** [sessões, cookies e validações](../../sauron_web/settings.py), [MFA](../../inventario/seguranca_mfa.py), [limites de login](../../inventario/infraestrutura/limites_login.py), Argon2id, [permissões](../../inventario/aplicacao/autorizacao.py), [auditoria HMAC](../../inventario/infraestrutura/auditoria.py) e [backup cifrado](../../inventario/infraestrutura/backup.py) existem. Âncoras, chaves, SMTP, TLS e restauração eficaz dependem da configuração e da operação real.
- **FATO:** o [workflow](../../.github/workflows/ci.yml) executa Django, pytest, lint, mypy parcial, Bandit, pip-audit, build/Compose e Trivy. Na [execução 43473391539](https://github.com/Luiz-Corticioni/testes_sauron_rede_neural/actions/runs/43473391539), validações e instalações passaram e o job de imagem falhou no Trivy; o log registrou 47 ocorrências HIGH e zero CRITICAL. Um pacote pode corresponder a múltiplos registros; não significam 47 explorações confirmadas. Resultado é pontual, não estado atual garantido.
- **FATO:** os [relatórios de Sprint 5](../SPRINT5_RASTREABILIDADE.md) e [fase de isca](../HONEYPOT_FASE1.md) documentam testes e pendências. Última suíte local relatada: 429 testes Django, seguida de 14 testes específicos; não equivalem a cobertura integral ou prova independente. Argon2 adiciona custo de memória; 100 usuários simultâneos sob limite de container não foram validados após a mudança.

## Pontos fortes, lacunas e riscos

1. **INFERÊNCIA:** a associação entre ativo, incidência, evidência, relações e hipóteses financeiras é útil para comunicar prioridades a equipes pequenas. É uma combinação observada no código, não vantagem comprovada sobre todos os produtos.
2. **INFERÊNCIA:** a separação explícita entre dados faltantes, hipóteses e probabilidade evita apresentar uma ausência de EPSS como risco zero; o modelo continua sujeito a dependências entre eventos e falta de calibração.
3. **FATO:** [ADR 009](../adr/009-telemetria.md) descreve ingestão autenticada como proposta; código de isca implementa apenas arquivo manual. **INFERÊNCIA:** não há base suficiente para prometer SIEM, EDR, detecção 24×7, resposta automática ou métricas SOC reais.
4. **FATO:** permissões são globais por modelo/grupo ([grupos](../../inventario/management/commands/configurar_grupos.py)); isolamento por organização/objeto não foi demonstrado. **INFERÊNCIA:** não oferecer hospedagem multiempresa até testar fronteiras por consulta, exportação, logs e backups.
5. **FATO:** a ordenação de risco da API v1 materializa registros e calcula/carrega risco global ([api_v1](../../inventario/web/api_v1.py)). **INFERÊNCIA:** paginação da resposta não limita necessariamente o custo da operação; medir com inventários grandes e cenários concorrentes.
6. **FATO:** o [seed operacional](../../inventario/aplicacao/demo_operacional.py) atribui autor e salva incidência; [Incidencia.save](../../inventario/models/incidencias.py) exige contexto de autoria. Na tentativa isolada de 13/11, `seed_demo --operacional` falhou com `Autoria da decisão deve corresponder ao usuário da operação`. **INFERÊNCIA:** é defeito reproduzido em um cenário de demonstração, não prova de falha generalizada de login; corrigir e testar separadamente.
7. **FATO:** `rg --files -g LICEN* -g COPYING*` não retornou licença de topo neste checkout. **INFERÊNCIA:** redistribuição e política comercial do Sauron estão indefinidas até decisão dos titulares; ausência de arquivo não autoriza assumir uma licença.
8. **INFERÊNCIA:** IPs de origem de iscas são sensíveis; falta retenção automatizada, segregação por organização e validação de fonte. O [guia](../HONEYPOT_FASE1.md) registra esses limites.

## Questões em aberto

- Quem é o operador e responsável por coleta, classificação, retenção e eliminação dos dados?
- Há homologação de backup/restauração, SMTP, TOTP e HTTPS **no servidor destinado**, e um teste de capacidade atualizado com Argon2? NÃO VERIFICADO.
- Há dados locais rotulados e confiáveis de perdas/incidentes para calibrar o modelo? NÃO VERIFICADO.
- Qual licença será escolhida para o próprio Sauron? NÃO VERIFICADO.
- Qual backend, volumes, número de usuários e requisitos de disponibilidade seriam contratados? NÃO VERIFICADO.

## Limitações da análise

Leitura estática e evidências anteriores; sem pentest, teste de carga prolongado, revisão jurídica, auditoria de todas as rotas, verificação de produção ou análise de custos. Ausência de evidência não é prova de ausência de defeito.
