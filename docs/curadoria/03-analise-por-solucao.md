# 03 — Análise por solução

[Diagnóstico](01-sauron-diagnostico.md) · [Métricas, release e licença de cada repositório](02-longlist-e-criterios.md) · [SOC](04-visao-soc.md)

A análise é documental, não foi feita instalação, benchmark, auditoria de código ou teste de detecção dos terceiros. Em cada seção, **FATO** é sustentado por fonte primária e **INFERÊNCIA** é avaliação aplicável ao Sauron. Data da coleta: 14/11/2026. Mantenedores atuais, capacidade real de detecção, falsos positivos, MTTD/MTTR e certificação no cenário do usuário: **NÃO VERIFICADOS** para todas as soluções. Estimativas de operação são relativas e não preço ou dimensionamento contratado.

## 1. Wazuh — SIEM/XDR e FIM

- **FATO:** [arquitetura oficial](https://documentation.wazuh.com/current/getting-started/architecture.html) descreve agente, servidor, indexador e dashboard; pode receber dados sem agente por fontes de rede. O [guia de instalação](https://documentation.wazuh.com/current/quickstart.html) apresenta faixas de hardware para laboratório, não um SLA. Serve à coleta e análise de eventos de endpoints e infraestrutura.
- **FATO:** eventos são processados por regras no servidor e enviados ao indexador; a própria documentação lista monitoramento de integridade e detecção de vulnerabilidades ([índice](https://documentation.wazuh.com/current/index.html)). O scanner e suas fontes não são equivalentes ao cadastro manual de incidências do Sauron.
- **FATO:** houve [advisory de execução remota por desserialização](https://github.com/wazuh/wazuh/security/advisories/GHSA-hcrc-79hj-m3qh), corrigido nas versões indicadas pelo aviso. A [licença por componente](https://github.com/wazuh/wazuh/blob/main/LICENSE) inclui engine AGPL e bibliotecas GPL/AGPL; conferir a versão efetiva instalada, distribuição e uso em rede.
- **INFERÊNCIA — pontos fortes/custo:** a coleta distribuída e retenção indexada ampliam observabilidade em relação à importação manual do Sauron; exige agentes, infraestrutura de indexação, atualizações, filas e tuning. A arquitetura declarada suporta implantação multinó, mas vazão, latência e FPs no ambiente do usuário são **NÃO VERIFICADOS**.
- **INFERÊNCIA — empresa:** segmentação, proteção de credenciais e revisão de RBAC/SSO/tenancy, retenção e conformidade dependem de versão/configuração. Não se conclui que estejam ausentes ou certificados. Cobertura ATT&CK quantificada e integrações específicas não examinadas: **NÃO VERIFICADO**.
- **Para Sauron:** priorizar importação de achados e eventos normalizados com origem, escopo e atualização; não incorporar agente ou recriar SIEM.

## 2. SigmaHQ — regras de detecção

- **FATO:** a [especificação Sigma](https://sigmahq.io/sigma-specification/specification/sigma-rules-specification.html) define `logsource`, condições, nível, referências, status e lista opcional de falsos positivos; a [especificação de correlação](https://sigmahq.io/sigma-specification/specification/sigma-correlation-rules-specification.html) alerta para risco de regras excessivamente ruidosas. O repositório é catálogo de regras, não um coletor ou SIEM por si só.
- **FATO:** as [regras usam DRL 1.1](https://github.com/SigmaHQ/sigma/blob/master/LICENSE), enquanto a especificação é declarada de domínio público nesse arquivo. Verificar obrigações da regra e seus derivados antes de distribuição comercial.
- **INFERÊNCIA — custo/limites:** portar o esquema de metadados e a disciplina de testes é barato; suportar a semântica Sigma inteira exigiria backend, mapeamento de campos, versões e validação. Não presumir que um motor simples interpreta todas as regras.
- **Detecção/empresa:** taxa de falso positivo, cobertura ATT&CK efetiva, desempenho do backend, CVEs, controle de acesso, SSO e retenção do ecossistema escolhido: **NÃO VERIFICADOS**. Tuning depende das fontes e pode reduzir ou elevar alertas.
- **Para Sauron:** começar com regras internas pequenas, versão, fonte, evidência, exemplo benigno e caso de teste; compatibilidade Sigma apenas após prova de paridade.

## 3. YARA-X — padrões em arquivos

- **FATO:** [YARA-X](https://virustotal.github.io/yara-x/docs/intro/getting-started/) é ferramenta de casamento de padrões por regras; seu [profiling](https://virustotal.github.io/yara-x/blog/profiling-your-yara-rules/) ajuda a identificar regras lentas, mas requer recursos de compilação específicos. [Licença BSD-3-Clause do repositório](https://github.com/VirusTotal/yara-x) não determina licença de cada conjunto de regras.
- **INFERÊNCIA:** adequado como motor externo e controlado de análise de arquivos; não substitui inventário, EDR ou regra de log. Upload de amostras introduz risco de exposição de dados, execução de parser e exaustão de recursos.
- **Detecção/escala:** cobertura ATT&CK, precisão, MTTD/MTTR e desempenho para os arquivos do usuário: **NÃO VERIFICADOS**; a existência de profiling não demonstra capacidade para qualquer volume. Histórico de advisories específico e SSO/RBAC/tenancy do serviço ao redor: **NÃO VERIFICADOS**.
- **Para Sauron:** não embutir motor de análise de malware agora. Caso exista necessidade real, importar metadados de resultado de uma ferramenta isolada com limites de tamanho e sem armazenar amostra por padrão.

## 4. MISP — inteligência de ameaças

- **FATO:** [MISP](https://github.com/MISP/MISP) descreve indicadores, correlação, grupos de partilha, API e importação/exportação STIX. Seu código central informa [AGPL-3.0](https://github.com/MISP/MISP/blob/2.5/LICENSE), com análise específica para distribuição e serviço modificado.
- **INFERÊNCIA:** proveniência, janela de validade, confiança e partilha são mais úteis ao Sauron do que reproduzir toda a plataforma. Indicador, IP ou coincidência não prova comprometimento; dados de terceiros podem estar desatualizados ou restritos por licença/partilha.
- **Operação:** servidor, gestão de comunidades, acesso às fontes e triagem geram custo; escalabilidade no cliente, taxa de FPs, cobertura ATT&CK e CVEs correntes **NÃO VERIFICADOS**. A existência de RBAC/API no README não comprova isolamento entre clientes, SSO, retenção ou conformidade do ambiente.
- **Para Sauron:** conector futuro somente de leitura, com consentimento, limites, `last_seen`, origem, expiração e alerta de dados obsoletos.

## 5. Greenbone/OpenVAS — varredura de vulnerabilidades

- **FATO:** a [arquitetura Greenbone](https://greenbone.github.io/docs/latest/background) separa scanner, daemon, gestor e interface; os testes dependem de feed. O [guia de troubleshooting](https://greenbone.github.io/docs/latest/troubleshooting.html) cita sincronização/recursos insuficientes entre causas de resultados ausentes. O [scanner](https://github.com/greenbone/openvas-scanner/blob/main/license-details.md) informa GPL-2.0 como licença efetiva do conjunto; verificar feeds e demais componentes individualmente.
- **INFERÊNCIA:** medições ativas complementariam o inventário, mas exigem escopo e autorização; resultado de scan é evidência de ferramenta, não confirmação automática. É mais racional consumir relatório que adicionar scanner próprio.
- **Qualidade/escala:** falsos positivos, cobertura técnica e impacto nos alvos, tempo de scan e histórico de CVEs completo: **NÃO VERIFICADOS**. Ativar scan em servidor compartilhado sem permissão não é aceitável.
- **Empresa:** multiempresa, RBAC, SSO, auditoria, retenção e certificações da edição concreta: **NÃO VERIFICADOS**; não extrapolar da edição comercial.
- **Para Sauron:** importar pequeno formato documentado, com identificação estável do scan, fonte e estado `pendente de confirmação`.

## 6. DefectDojo — gestão de achados

- **FATO:** o [repositório](https://github.com/DefectDojo/django-DefectDojo) descreve gestão unificada de vulnerabilidades em aplicação Python/Django; a [documentação de deduplicação](https://docs.defectdojo.com/triage_findings/finding_deduplication/about_deduplication/) trata da identificação de achados repetidos. A API identifica licença BSD-3-Clause do repositório; a documentação diferencia recursos Open Source e Pro, e ampliações como alguns escopos de deduplicação são indicadas como Pro. Verificar componentes e edição usados.
- **FATO:** um [advisory](https://github.com/DefectDojo/django-DefectDojo/security/advisories/GHSA-4859-jfm8-m5xp) registra leitura de arquivos por administrador autenticado em versões anteriores e correção indicada pelo projeto. Um projeto de segurança também requer atualização.
- **INFERÊNCIA:** estados, deduplicação e rastreio de fonte são boas referências para Sauron; deduplicação excessiva pode ocultar incidências distintas. Retenção, multiempresa, SSO e controles da edição escolhida precisam de validação.
- **Detecção/operação:** o produto gerencia achados, não comprova taxa de detecção dos scanners; FP, desempenho e ganhos de tempo no cenário local **NÃO VERIFICADOS**. Importadores e formatos exigem manutenção e análise de dados não confiáveis.
- **Para Sauron:** preservar identificador de origem por scan, confirmação humana e histórico de transição, com testes de colisão e reimportação.

## 7. Cowrie — honeypot SSH/Telnet

- **FATO:** [Cowrie](https://github.com/cowrie/cowrie) descreve emulação de interação SSH/Telnet; [eventos de saída](https://docs.cowrie.org/en/latest/OUTPUT.html) incluem tipo, sessão, timestamp e origem. O campo `eventid` identifica o **tipo**, não é ID único de ocorrência: não pode ser usado sozinho como chave de deduplicação.
- **FATO:** a [política de segurança](https://github.com/cowrie/cowrie/security) inclui risco de escape e dependências; houve [advisory de SSRF](https://github.com/cowrie/cowrie/security/advisories/GHSA-83jg-m2pm-4jxj). Licença BSD declarada com [detalhes por arquivo](https://github.com/cowrie/cowrie/blob/main/LICENSE.rst).
- **INFERÊNCIA:** boa fonte para um adaptador futuro; eventos podem conter credenciais e comandos, portanto minimização antes da persistência, rede segregada e controle de saída são essenciais. Não usar o serviço isca como sensor de produção no servidor acadêmico sem autorização.
- **Qualidade/empresa:** ação sobre isca pode refletir teste, varredura ou ataque; falsos positivos, cobertura ATT&CK, tempo de decisão e capacidade **NÃO VERIFICADOS**. SSO, multiempresa e retenção no stack completo também.
- **Para Sauron:** a fase atual importa formato próprio, sem conector. Um replay local deve gerar ID determinístico a partir de sensor, sessão, posição/identificador de origem e payload minimizado, preservando colisões distintas e descartando segredos.

## 8. IntelOwl — enriquecimento e análise de observáveis

- **FATO:** [IntelOwl](https://github.com/intelowlproject/IntelOwl) lista analisadores internos e externos; a [documentação de uso](https://intelowlproject.github.io/docs/IntelOwl/usage/) descreve jobs, analisadores e conectores. A [configuração](https://intelowlproject.github.io/docs/IntelOwl/advanced_configuration/) menciona banco/broker e configuração por plugin. O repositório indica [AGPL-3.0](https://github.com/intelowlproject/IntelOwl/blob/master/LICENSE).
- **FATO:** a [release v6.8.0](https://github.com/intelowlproject/IntelOwl/releases/tag/v6.8.0) menciona ausência de suporte ARM naquele build; não inferir suporte em outras releases. Alguns analisadores externos exigem credenciais, conforme [configuração avançada](https://intelowlproject.github.io/docs/IntelOwl/advanced_usage/).
- **INFERÊNCIA:** o modelo de jobs, resultado parcial e plugins ajuda a não bloquear a interface em chamadas externas. Custos de provedor, dados enviados, licenças e segredos exigem opt-in; não habilitar serviços pagos ou API OpenAI por padrão.
- **Qualidade/empresa:** precisão por conector, SLA, volume, CVEs completos e certificações **NÃO VERIFICADOS**; um resultado agregado não substitui avaliação de fonte.
- **Para Sauron:** fila limitada, timeout, estado por fonte e reprocessamento idempotente, inicialmente com feeds já usados e sem serviços pagos.

## 9. IVRE — inventário de observações de rede

- **FATO:** o [README do IVRE](https://github.com/ivre/ivre) lista dados de fontes passivas e ativas; a [documentação](https://doc.ivre.rocks/_/downloads/en/stable/pdf/) descreve visão consolidada de hosts. A API aponta GPL-3.0 para o repositório. A release `v0.9.21` consultada é antiga, embora haja commits recentes ([atividade](https://github.com/ivre/ivre/commits/master/)); conferir versão distribuída e manutenção antes de implantar.
- **INFERÊNCIA:** diferenciar fonte de observação, inventário desejado e estado confirmado é particularmente útil para evitar inventar topologia no Sauron. Um IP não é identidade definitiva e dados passivos podem estar incompletos.
- **Detecção/empresa:** capacidade de volume, falsos positivos, cobertura ATT&CK, histórico completo de CVEs, isolamento entre organizações e SSO **NÃO VERIFICADOS**. A operação de sensores e scanners exige autorização, rede e pessoal.
- **Para Sauron:** modelo de observação independente com fonte, horário e confiança, vinculação revisável e registro de conflitos; não fazer descoberta ativa por padrão.

## Limitações e licenças

Não foram examinados todos os commits, todos os advisories, os termos de cada feed/regra, nem a edição exata e os módulos que um cliente instalaria. Ausência de CVE listado aqui não significa ausência de CVEs. Não se afirma conformidade com LGPD, ISO 27001, SOC 2 ou PCI: conformidade depende do ambiente, contratos e processos. Licenças copyleft permitem uso comercial sob condições; interface de rede, incorporação, distribuição de binários, conteúdo e modificações precisam de análise jurídica. Nenhum código externo foi executado ou copiado.
