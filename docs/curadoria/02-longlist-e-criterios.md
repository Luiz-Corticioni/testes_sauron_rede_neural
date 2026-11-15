# Longlist e critérios

[Resumo](00-resumo-executivo.md) · [Diagnóstico](01-sauron-diagnostico.md) · [Análise](03-analise-por-solucao.md)

**Consulta:** 14/11/2026. Longlist: 20 repositórios GitHub; 9 finalistas. Não é uma amostra de mercado nem ranking de produtos. Fonte de cada linha: link do repositório; metadados foram consultados pela API REST do próprio GitHub (`/repos/{owner}/{repo}`, `/commits`, `/releases/latest`, `/contributors` e `/search/issues`). [Instantâneo estruturado](dados-repositorios.json). Os valores podem mudar.

**Leitura das métricas:** `90d` conta a primeira página de commits da branch padrão desde 16/08/2026 UTC; `100+` significa ao menos 100 retornados, não contagem total. A coluna colaboradores é apenas a primeira página da API e pode incluir histórico/bots: **não é número de mantenedores**. Mantenedores atuais: número total NÃO VERIFICADO para cada linha; a API pública consultada não fornece lista homogênea de responsáveis ativos. O [README do Cowrie](https://github.com/cowrie/cowrie) identifica Michel Oosterhof como mantenedor; isso confirma ao menos um nome, não o tamanho da equipe. Issues são buscas de issues abertas/fechadas, sem PRs, sujeitas a configuração e indexação; 0/0 não prova ausência de problemas (Suricata pode usar outros rastreadores). Estrelas são contexto, não qualidade. Linguagem é a principal informada pelo GitHub, não necessariamente a linguagem das regras. Release usa o endpoint `latest`, que pode não representar o artefato ideal para produção. `NOASSERTION` significa que a API não identificou uma licença SPDX única: condições específicas precisam de revisão; não equivale a uma licença permissiva.

| Repositório | Escopo | Licença indicada | Linguagem | Estrelas | Último commit UTC | Última release | 90d | Issues A/F | Colaboradores 1ª pág. | Finalista |
|---|---|---|---|---:|---|---|---:|---|---:|---|
| [wazuh/wazuh](https://github.com/wazuh/wazuh) | SIEM/XDR/FIM | mista: AGPL-3.0-or-later/GPL-2.0 | C++ | 17740 | 2026-11-14 | v4.14.10 · 2026-11-09 | 100+ | 3008/24735 | 100+ | Sim |
| [SigmaHQ/sigma](https://github.com/SigmaHQ/sigma) | regras de logs | DRL 1.1 (regras); especificação domínio público | Python | 11508 | 2026-11-13 | r2026-07-01 · 2026-07-09 | 100+ | 12/668 | 100+ | Sim |
| [VirusTotal/yara-x](https://github.com/VirusTotal/yara-x) | assinaturas de arquivo | BSD-3-Clause | Rust | 1366 | 2026-11-14 | v1.23.0 · 2026-11-05 | 100+ | 25/290 | 54 | Sim |
| [MISP/MISP](https://github.com/MISP/MISP) | inteligência de ameaças | AGPL-3.0 | PHP | 6665 | 2026-11-01 | v2.5.51 · 2026-11-11 | 100+ | 2710/4355 | 100+ | Sim |
| [greenbone/openvas-scanner](https://github.com/greenbone/openvas-scanner) | scanner | GPL-2.0 | Rust | 4943 | 2026-11-12 | v23.52.12 · 2026-11-12 | 100+ | 7/198 | 58 | Sim |
| [DefectDojo/django-DefectDojo](https://github.com/DefectDojo/django-DefectDojo) | gestão de vulnerabilidades | BSD-3-Clause | Python | 5234 | 2026-11-13 | 3.5.103 · 2026-11-13 | 100+ | 205/3083 | 100+ | Sim |
| [cowrie/cowrie](https://github.com/cowrie/cowrie) | honeypot | BSD (detalhes por arquivo) | Python | 6680 | 2026-11-14 | v3.1.6 · 2026-11-09 | 100+ | 39/1153 | 100+ | Sim |
| [intelowlproject/IntelOwl](https://github.com/intelowlproject/IntelOwl) | enriquecimento | AGPL-3.0 | Python | 4819 | 2026-09-02 | v6.8.0 · 2026-08-31 | 9 | 46/823 | 100+ | Sim |
| [ivre/ivre](https://github.com/ivre/ivre) | superfície/recon | GPL-3.0 | Python | 4206 | 2026-09-10 | v0.9.21 · 2024-09-25 | 4 | 39/322 | 41 | Sim |
| [falcosecurity/falco](https://github.com/falcosecurity/falco) | detecção runtime | Apache-2.0 | C++ | 9579 | 2026-11-06 | 0.45.2 · 2026-10-29 | 87 | 29/1435 | 100+ | Não |
| [OISF/suricata](https://github.com/OISF/suricata) | IDS/IPS | GPL-2.0 | C | 6891 | 2026-11-11 | suricata-8.0.8 · 2026-10-29 | 100+ | 0/0 | 100+ | Não |
| [zeek/zeek](https://github.com/zeek/zeek) | telemetria de rede | NOASSERTION | C++ | 8240 | 2026-11-13 | v9.0.1 · 2026-10-26 | 100+ | 242/1654 | 100+ | Não |
| [Shuffle/Shuffle](https://github.com/Shuffle/Shuffle) | SOAR | AGPL-3.0 | JavaScript | 2481 | 2026-11-10 | v2.3.0 · 2026-09-28 | 100+ | 486/774 | 41 | Não |
| [OpenCTI-Platform/opencti](https://github.com/OpenCTI-Platform/opencti) | CTI | NOASSERTION | TypeScript | 10369 | 2026-11-14 | 7.261109.0 · 2026-11-09 | 100+ | 2037/7875 | 100+ | Não |
| [osquery/osquery](https://github.com/osquery/osquery) | telemetria host | NOASSERTION | C++ | 23766 | 2026-11-12 | 5.24.1 · 2026-10-29 | 100+ | 492/3209 | 100+ | Não |
| [ossec/ossec-hids](https://github.com/ossec/ossec-hids) | HIDS | GPL-2.0 | C | 5071 | 2026-11-12 | 4.4.1 · 2026-10-18 | 100+ | 31/1015 | 100+ | Não |
| [cilium/tetragon](https://github.com/cilium/tetragon) | observabilidade eBPF | Apache-2.0 | C | 5184 | 2026-11-14 | v1.8.0 · 2026-10-30 | 100+ | 146/725 | 100+ | Não |
| [projectdiscovery/nuclei](https://github.com/projectdiscovery/nuclei) | scanner templates | MIT | Go | 32918 | 2026-11-14 | v3.11.1 · 2026-08-08 | 100+ | 61/3059 | 100+ | Não |
| [DependencyTrack/dependency-track](https://github.com/DependencyTrack/dependency-track) | SBOM/SCA | Apache-2.0 | Java | 4458 | 2026-11-14 | 5.2.1 · 2026-10-25 | 100+ | 852/2000 | 100+ | Não |
| [anchore/grype](https://github.com/anchore/grype) | scanner de componentes | Apache-2.0 | Go | 13265 | 2026-11-14 | v0.121.3 · 2026-11-09 | 100+ | 351/931 | 100+ | Não |

## Decisões de seleção e descarte

- **wazuh/wazuh:** Finalista: arquitetura SIEM e inventário de endpoints.
- **SigmaHQ/sigma:** Finalista: contrato de regra e documentação de falso positivo.
- **VirusTotal/yara-x:** Finalista: delimita padrões de arquivos e custo de execução.
- **MISP/MISP:** Finalista: qualidade, partilha e proveniência de inteligência.
- **greenbone/openvas-scanner:** Finalista: scanner externo e feed, não duplicar coleta.
- **DefectDojo/django-DefectDojo:** Finalista: ciclo de achados, deduplicação e produto Django.
- **cowrie/cowrie:** Finalista: integração com a fase de iscas.
- **intelowlproject/IntelOwl:** Finalista menor: execução de enriquecimentos e falhas por conector.
- **ivre/ivre:** Finalista menor: conciliação de visões passiva/ativa; poucos commits e release antiga exigem ressalva.
- **falcosecurity/falco:** Fora da profundidade: runtime é distante da prioridade de inventário.
- **OISF/suricata:** Fora: sensor de rede operacional exigiria infraestrutura própria.
- **zeek/zeek:** Fora: telemetria de rede sobrepõe SIEM/IVRE nesta rodada.
- **Shuffle/Shuffle:** Fora: automação de resposta é prematura sem ingestão confiável.
- **OpenCTI-Platform/opencti:** Fora: sobrepõe MISP e amplia custo de plataforma.
- **osquery/osquery:** Fora: coleta em endpoints exige agente; priorizado Wazuh.
- **ossec/ossec-hids:** Fora: escopo sobrepõe Wazuh; não é juízo de qualidade.
- **cilium/tetragon:** Fora: foco eBPF/container não é requisito imediato.
- **projectdiscovery/nuclei:** Fora: varredura ativa exige autorização; OpenVAS cobre scanner representativo.
- **DependencyTrack/dependency-track:** Fora: SBOM é relevante, mas reduzimos sobreposição com DefectDojo.
- **anchore/grype:** Fora: scanner de dependências representa parte do escopo coberto pelos selecionados.

A atividade em 90 dias e o último commit foram usados como triagem; não qualificam, por si, manutenção segura. Nenhum foi excluído automaticamente como abandonado por falta de commits em 18 meses. **IVRE:** última release apontada pelo endpoint é de 25/09/2024, embora haja quatro commits recentes na página, incluindo correção de parsing e atualização de dependências; isso não comprova prontidão comercial nem release contendo tais mudanças. É mantido pelo valor da distinção entre fontes de observação e pela amostra relativamente menor. **YARA-X:** cerca de 1,4 mil estrelas, menor na amostra; a ideia selecionada é a análise de regras lentas por profiling, descrita na [documentação do projeto](https://virustotal.github.io/yara-x/blog/profiling-your-yara-rules/). **IntelOwl:** nove commits na janela e cerca de 4,8 mil estrelas; a ideia é representar execução e falha por analisador ([documentação](https://intelowlproject.github.io/docs/IntelOwl/usage/)). Números são contexto, não prova de inovação ou adoção operacional. Adoção real independente, número de instalações, qualidade de governança e mantenedores: NÃO VERIFICADOS.

## Licenças e Bitbucket

A licença do repositório não cobre automaticamente todas as dependências, feeds, regras ou serviços. [Wazuh](https://github.com/wazuh/wazuh/blob/main/LICENSE) declara engine AGPL e bibliotecas com opções GPL/AGPL; [Sigma](https://github.com/SigmaHQ/sigma/blob/master/LICENSE) indica DRL 1.1 para as regras e domínio público para a especificação. Cowrie usa [licenciamento por arquivos](https://github.com/cowrie/cowrie/blob/main/LICENSE.rst); a API retornou NOASSERTION e não foi atribuído um SPDX único sem verificar cada componente. Essas licenças não significam automaticamente proibição de venda: distribuição, obra derivada, disponibilização em rede e regras de conteúdo têm obrigações diferentes; revisar com assessoria jurídica antes de redistribuir ou integrar.

A busca Bitbucket retornou resultados com páginas genéricas de Snyk e o candidato público [AIEngine](https://bitbucket.org/camp0/aiengine/), mas a API pública do repositório não ficou acessível à ferramenta usada. Licença, último commit, mantenedores e maturidade do candidato: **NÃO VERIFICADOS**; por isso não entrou na tabela comparável nem foi declarado abandonado. A busca é limitada e não prova que o Bitbucket não contenha outros projetos adequados.
