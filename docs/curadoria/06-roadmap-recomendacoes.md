# 06 — Roadmap de recomendações

[Diagnóstico](01-sauron-diagnostico.md) · [Análises com fontes](03-analise-por-solucao.md) · [Perspectiva SOC](04-visao-soc.md)

Isto é proposta, não implementação. **Esforço** supõe uma pessoa familiarizada com Django e ambiente de teste disponível: P até 3 dias úteis; M 4–10; G mais de 10. Não inclui aquisição/aprovação de infraestrutura, homologação jurídica ou dados. Impacto e risco são julgamento; metas são critérios propostos, **não resultados medidos**. Quick wins até duas semanas exigem seleção por capacidade e não cabem necessariamente todos na mesma quinzena.

## Quick wins — primeira janela de até duas semanas

### Q1. Corrigir e testar seed operacional

- **Problema/ação:** `seed_demo --operacional` falhou em teste isolado por autoria. Ajustar criação para usar o serviço/contexto de autoria adequado, sem relaxar a regra de decisão.
- **Referência:** [código atual](../../inventario/aplicacao/demo_operacional.py), [invariante](../../inventario/models/incidencias.py); prioridade deriva da demonstração, não de recurso externo.
- **Onde:** `inventario/aplicacao/demo_operacional.py`, `tests/` e guia. **P; impacto alto; risco médio:** uma solução inadequada poderia permitir aprovação fictícia ou burlar segregação. **Dependência:** fixture em base descartável.
- **Aceite:** executar migrações e `seed_demo --operacional` em base vazia, validar que dados são identificados como simulados e que segunda execução não sobrescreve inventário real; teste de falha garante rollback e cadeia íntegra.

### Q2. Tornar estado da fonte e lacunas visíveis

- **Problema/ação:** mostrar última atualização, origem, idade, falha e cobertura de NVD/KEV/EPSS e da importação de iscas. Não mostrar “seguro” quando dado estiver ausente.
- **Inspiração:** [feeds Greenbone e sincronização](https://greenbone.github.io/docs/latest/troubleshooting.html), [observações IVRE](https://github.com/ivre/ivre); [fontes existentes](../../inventario/infraestrutura/cve_client.py).
- **Onde:** `inventario/aplicacao/epss.py`, `inventario/infraestrutura/cve_client.py`, `inventario/web/` e templates. **M; impacto alto; risco baixo/médio:** falso estado saudável se falhas forem engolidas. **Dependência:** definir tempos por fonte e relógio UTC.
- **Aceite:** fixtures de sucesso, dado vencido, fonte inacessível e lista vazia resultam em quatro estados visíveis; nenhuma faz atualização falsa nem oculta erro.

### Q3. Resolver scan da própria imagem com critério

- **Problema/ação:** avaliar os 47 registros HIGH da última CI do commit-base; atualizar componentes corrigíveis, documentar os sem correção e sua aplicabilidade. Não desligar o Trivy.
- **Inspiração:** [advisory DefectDojo](https://github.com/DefectDojo/django-DefectDojo/security/advisories/GHSA-4859-jfm8-m5xp), [issue interna #13](https://github.com/Luiz-Corticioni/testes_sauron_rede_neural/issues/13).
- **Onde:** `Dockerfile`, `.github/workflows/ci.yml`, documentação de segurança. **M; impacto alto; risco médio:** upgrade de SO pode quebrar dependências ou perder cobertura. **Dependência:** Docker/runner, IDs concretos e política aprovada para exceção.
- **Aceite:** relatório por CVE/pacote com versão, status do fornecedor e justificativa verificável; scan reproduzível, smoke tests e teste de rollback. CI só fica verde se política acordada for realmente atendida.

### Q4. Medir custo de login com Argon2 em limite real

- **Problema/ação:** repetir teste de 100 contas e MFA com limites do Compose, medindo RAM, erros 429/OOM e latências; não reduzir custo do hash para fabricar resultado.
- **Inspiração:** [instalação Wazuh explicita dimensionamento por cenário](https://documentation.wazuh.com/current/quickstart.html); ensaio atual em [fase 7](../RELATORIO_FASE7_CARGA_CACHE.md) é anterior ao Argon2.
- **Onde:** `scripts/testar_carga.py`, `compose.yaml`, `docs/`. **M; impacto alto; risco médio:** teste pode esgotar host; executar em máquina/container descartável com limites. **Dependência:** ambiente Docker autorizado e orçamento de RAM.
- **Aceite:** publicar método, p50/p95, número de sessões concluídas, 429, RAM de pico e falhas para pelo menos duas configurações; declarar se 100 usuários atendem ao critério acordado, sem extrapolar.

### Q5. Padronizar triagem de isca sem fingir integração

- **Problema/ação:** acrescentar classificação manual `teste autorizado`, `suspeito`, `inconclusivo` e observação sucinta; separar evento de alerta e preservar autoria; política de retenção antes de dados reais.
- **Inspiração:** [campos e sessão Cowrie](https://docs.cowrie.org/en/latest/OUTPUT.html); [serviço Sauron](../../inventario/aplicacao/honeypot.py).
- **Onde:** `inventario/models/honeypot.py`, serviço, migração, views, testes e guia. **M; impacto médio; risco médio:** expor IP/rotular indevidamente. **Dependência:** papéis e decisão de retenção.
- **Aceite:** usuário sem permissão recebe 403; cada revisão gera auditoria; 100% das amostras sintéticas ficam separadas de casos reais; nenhuma senha/comando é persistido.

## Médio prazo — após quick wins e autorização

### M1. Contrato de observação e proveniência

- **Ação:** definir esquema versionado para origem, tipo, `observado_em`, `recebido_em`, identidade do sensor, identificador estável, confiança e erro; separar observação de fato confirmado. Mapear casos necessários de ECS/OCSF, sem alegar conformidade integral.
- **Inspiração:** [IVRE](https://github.com/ivre/ivre), [pipeline Cowrie](https://docs.cowrie.org/en/latest/EVENT_PIPELINE.html), [ADR 009](../adr/009-telemetria.md). **Onde:** novo módulo de domínio/aplicação e modelos; `inventario/aplicacao/honeypot.py`. **G; impacto alto; risco alto:** migração, duplicatas e dados sensíveis. **Dependência:** retenção e política de identidade.
- **Aceite:** 200 fixtures com timestamps fora de ordem, duplicadas, conflito de ID e campo proibido têm resultado determinístico; lote inválido não deixa gravação parcial; consulta mostra origem/data. O número é meta de teste proposta.

### M2. Importar relatórios de scanner, não executar scans

- **Ação:** prototipar importador offline de um único formato de relatório autorizado; manter origem, escopo, versão e evidência; criar sugestão revisável, não incidência confirmada automaticamente.
- **Inspiração:** [Greenbone](https://greenbone.github.io/docs/latest/background), [deduplicação DefectDojo](https://docs.defectdojo.com/triage_findings/finding_deduplication/about_deduplication/). **Onde:** `inventario/aplicacao/documentos.py`, modelos de achados, forms/views e testes. **G; impacto alto; risco alto:** parser, identidade errada, duplicação. **Dependência:** amostras sintéticas e especificação/formato/licença verificados.
- **Aceite:** reimportação idêntica não cria duplicata; versões conflitantes permanecem separadas; entrada truncada/maior que limite é rejeitada; aceite humano obrigatório.

### M3. Conector Cowrie por replay, sem rede no início

- **Ação:** adaptador local converte um conjunto mínimo de campos dos eventos nativos para esquema M1; `eventid` é tipo, não identidade única. Não guardar `password`, `username` ou comandos por padrão.
- **Inspiração:** [eventos Cowrie](https://docs.cowrie.org/en/latest/OUTPUT.html) e [advisory SSRF](https://github.com/cowrie/cowrie/security/advisories/GHSA-83jg-m2pm-4jxj). **Onde:** `inventario/infraestrutura/`, `inventario/aplicacao/honeypot.py`, testes. **M/G; impacto médio; risco alto:** segredos e fuga de rede. **Dependência:** M1, fixture sanitizada e ambiente isolado; não é implantação pública.
- **Aceite:** replay de fixtures com dois eventos do mesmo tipo/sessão preserva ambos; repetição dos mesmos IDs não duplica; dados proibidos nunca são gravados; teste mostra que falha de parser não produz alerta parcial.

### M4. Estados de regra e evidência para triagem

- **Ação:** catálogo interno pequeno, versão, status, condição, evidência, origem e exemplos benignos; UI permite justificar reconhecimento/ajuste e registrar falso positivo.
- **Inspiração:** [status e falsos positivos Sigma](https://sigmahq.io/sigma-specification/specification/sigma-rules-specification.html); [alertas](../../inventario/aplicacao/operacao.py). **Onde:** modelos e serviços de alerta, views, testes. **G; impacto médio; risco alto:** regras frágeis ou incentivo a silenciar. **Dependência:** M1, dados rotulados e limites de execução.
- **Aceite:** toda regra habilitada tem proprietário, versão e ao menos um teste positivo e negativo; alteração/reconhecimento é auditada; desativação não apaga histórico. Compatibilidade Sigma completa não é promessa desta fase.

### M5. API e identidade para integração

- **Ação:** decidir entre integração via arquivo, API de leitura ou serviço externo; para escrita, projetar credenciais com escopo/rotação/revogação e limites, preservando sessão/MFA da interface e permissões dos serviços.
- **Inspiração:** [API e partilha MISP](https://github.com/MISP/MISP), [API v1 local](../../inventario/web/api_v1.py). **Onde:** `inventario/web/`, `inventario/seguranca*`, OpenAPI, testes. **G; impacto alto; risco alto:** credencial de máquina contornando MFA ou autorização. **Dependência:** ameaça, desenho de revogação e necessidade real.
- **Aceite:** testes de token/credencial inválida, expirada, revogada, sem escopo e tentativa entre organizações; operações sensíveis continuam auditadas. Não implementar JWT apenas para atender moda.

## Apostas estratégicas — condicionadas a evidência

### E1. Isolamento de organizações e operação empresarial

- **Ação:** escopo por organização em consultas, objetos, tarefas, cache, exports, backups e auditoria; identidade/SSO somente quando houver requisito.
- **Referência:** [MISP descreve grupos de partilha](https://github.com/MISP/MISP); isso não comprova adequação do MISP ao cliente. **Onde:** todos os modelos, serviços e controles, migrações e infraestrutura. **G; impacto alto; risco muito alto:** vazamento entre clientes. **Dependência:** modelo de negócio, ameaças e revisão independente.
- **Aceite:** matriz automatizada cobre leitura, escrita, busca, exports, cache e backup entre ao menos duas organizações; testes de abuso e restauração passam, com revisão externa antes de SaaS.

### E2. Calibração financeira com dados locais

- **Ação:** manter 30 dias, distinguir EPSS de probabilidade por ativo, registrar distribuições, dependências e qualidade das entradas; testar cenários com correlações e comparar com dados observados quando disponíveis.
- **Referência:** [modelo atual](../../inventario/matematica/montecarlo.py), não uma afirmação sobre ferramentas externas. **Onde:** `inventario/matematica/montecarlo.py`, `inventario/aplicacao/montecarlo.py`, dashboard, testes. **G; impacto alto; risco alto:** apresentar previsão tendenciosa como fato. **Dependência:** dados anonimizados e validação de especialistas de risco.
- **Aceite:** documentação mostra hipóteses e exemplos de sensibilidade; testes reprodutíveis com seed e casos sem dados; calibração só declarada após comparação com histórico e revisão independente.

## O que não fazer agora

- Não prometer que Sauron substitui Wazuh/Greenbone, construir agente, SIEM ou motor de malware do zero: [Wazuh](https://documentation.wazuh.com/current/getting-started/architecture.html) e [Greenbone](https://greenbone.github.io/docs/latest/background) já exigem arquitetura e operação específicas; antes falta ingestão confiável.
- Não ligar honeypot publicamente ou fazer scan ativo sem autorização; em particular, o servidor compartilhado não foi disponibilizado para isso. Não executar payload capturado.
- Não copiar regras sem avaliar a [licença DRL Sigma](https://github.com/SigmaHQ/sigma/blob/master/LICENSE) ou empacotar código GPL/AGPL sem revisão da distribuição e dos termos aplicáveis.
- Não usar APIs pagas nem OpenAI para enriquecer dados por padrão; custo e envio de dados são escolhas explícitas do usuário.
- Não derivar probabilidade de invasão, MTTD/MTTR ou conformidade de um CVSS, alerta isolado, estrela ou porcentagem de cobertura não medida.

## Limitações

Estimativas e limites são metas propostas, não garantia de tempo ou desempenho. Ordem pode mudar após medições, aprovação da infraestrutura e definição de dados/usuários. Nenhuma das tarefas foi executada como parte desta curadoria.
