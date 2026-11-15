# 05 — Matriz comparativa e posicionamento

[Diagnóstico do Sauron](01-sauron-diagnostico.md) · [Fontes dos finalistas](03-analise-por-solucao.md) · [Roadmap](06-roadmap-recomendacoes.md)

Esta matriz compara **escopo comprovado na amostra**, não qualidade, segurança ou prontidão de produção. `●` função explicitamente documentada/examinada; `◐` parte restrita; `?` não verificado ou não aplicável na análise. **Não interprete `?` como recurso inexistente.** Links das linhas levam às fontes detalhadas. Financeiro refere-se a cenários explícitos de perdas monetárias, não a todas as formas de priorização.

| Solução | Inventário / achados | Coleta de eventos / observações | Regras de detecção ou padrões | Inteligência / contexto | Tratamento / revisão | Cenários monetários |
|---|---|---|---|---|---|---|
| [Sauron](01-sauron-diagnostico.md) | ● | ◐ arquivo manual de isca | ◐ alertas por condições internas | ◐ NVD/KEV/EPSS/SSVC | ● estado e revisão | ◐ 30 dias, hipóteses |
| [Wazuh](03-analise-por-solucao.md#1-wazuh--siemxdr-e-fim) | ● inventário documentado | ● agentes e rede | ● regras servidor | ◐ feed de vulnerabilidades | ? | ? |
| [SigmaHQ](03-analise-por-solucao.md#2-sigmahq--regras-de-detecção) | ? | ? | ● formato de regra, depende de backend | ◐ referências e tags | ? | ? |
| [YARA-X](03-analise-por-solucao.md#3-yara-x--padrões-em-arquivos) | ? | ? | ● padrões de arquivo | ? | ? | ? |
| [MISP](03-analise-por-solucao.md#4-misp--inteligência-de-ameaças) | ◐ indicadores/eventos | ◐ importação de fontes | ? | ● compartilhamento e contexto | ◐ revisão/partilha | ? |
| [Greenbone](03-analise-por-solucao.md#5-greenboneopenvas--varredura-de-vulnerabilidades) | ● resultados de scan | ● varredura ativa | ● testes de vulnerabilidade | ◐ feeds | ? | ? |
| [DefectDojo](03-analise-por-solucao.md#6-defectdojo--gestão-de-achados) | ● achados | ◐ importação de resultados | ? | ? | ● triagem e deduplicação | ? |
| [Cowrie](03-analise-por-solucao.md#7-cowrie--honeypot-sshtelnet) | ? | ● interações da isca | ? | ◐ eventos contextuais | ? | ? |
| [IntelOwl](03-analise-por-solucao.md#8-intelowl--enriquecimento-e-análise-de-observáveis) | ◐ jobs/observáveis | ◐ submissão a analisadores | ◐ analisadores/plugins | ● enriquecimento | ◐ jobs e conectores | ? |
| [IVRE](03-analise-por-solucao.md#9-ivre--inventário-de-observações-de-rede) | ● visões de hosts | ● fontes ativas/passivas | ? | ◐ contexto de rede | ? | ? |

## Onde o Sauron já tem base útil

**FATO:** os modelos e serviços reúnem inventário, dependências, decisão sobre incidência e um painel de cenários financeiros ([diagnóstico](01-sauron-diagnostico.md)). O código explicita limites do modelo financeiro e sinaliza EPSS ausente. **INFERÊNCIA:** essa composição é útil em reuniões de priorização de um inventário pequeno, mas não há estudo comparativo que prove ser exclusiva, superior ou mais precisa que plataformas selecionadas. Não foi verificado se os demais possuem seus próprios módulos financeiros.

## Onde está atrás e consequência prática

- **FATO:** [Wazuh documenta agentes e indexação](https://documentation.wazuh.com/current/getting-started/architecture.html); [Sauron tem importação manual de eventos de isca](../../inventario/aplicacao/honeypot.py). **INFERÊNCIA:** o Sauron não deve ser apresentado como substituto de monitoramento contínuo de endpoints.
- **FATO:** [OpenVAS executa testes de vulnerabilidade](https://greenbone.github.io/docs/latest/background); o Sauron mantém incidências e fontes de enriquecimento ([modelos](../../inventario/models/incidencias.py)). **INFERÊNCIA:** cadastros podem ficar desatualizados sem coleta e validação externas.
- **FATO:** [Sigma define contrato compartilhável de regras](https://sigmahq.io/sigma-specification/specification/sigma-rules-specification.html); [ADR de telemetria](../adr/009-telemetria.md) do Sauron é proposta. **INFERÊNCIA:** não há base para prometer compatibilidade Sigma ou cobertura ATT&CK quantitativa.
- **FATO:** [v1 do Sauron](../../inventario/web/api_v1.py) oferece leitura e [contrato parcial](../openapi-v1.json). **INFERÊNCIA:** integração automatizada abrangente exige desenho de autenticação, escrita e manutenção de contrato.
- **FATO:** [CI do commit anterior](https://github.com/Luiz-Corticioni/testes_sauron_rede_neural/actions/runs/43473391539) reprovou no scan da imagem. **INFERÊNCIA:** uma proposta comercial séria precisa explicitar o risco residual e seu responsável.

## Espaços para explorar, sem alegar lacuna comprovada do mercado

1. **INFERÊNCIA:** uma explicação curta ligando ativo → evidência → dependência → hipótese financeira → decisão, com incerteza e data da fonte, pode ser clara para gestor e analista. Outros projetos podem oferecer partes ou tudo isso; exclusividade **NÃO VERIFICADA**.
2. **INFERÊNCIA:** manter revisões de cobertura de topologia separadas de suposições de segurança pode evitar que dados ausentes pareçam isolamento. Valor depende de teste com usuários.
3. **INFERÊNCIA:** tratar demonstração e observação real como classes distintas evita usar amostra sintética como incidente. Isso não é diferencial exclusivo.

## Para quem serve hoje

**INFERÊNCIA:** protótipo acadêmico e avaliação controlada com dados fictícios ou ambiente pequeno autorizado, operador técnico, backup e supervisão. Testes e controles existentes não substituem homologação. **Não indicado ainda** como SIEM/EDR autônomo, plataforma SOC 24×7 ou SaaS multiempresa com garantia de conformidade; faltam validação operacional, isolamento, telemetria contínua e medições. Para uma empresa real, seria necessário piloto controlado com limites e responsáveis, não implantação presumida.

## Limitações

Sem prova de conceito dos produtos, comparativo de preços, teste de campo, cobertura ATT&CK equivalente, qualidade estatística ou auditoria de conformidade. `●` não significa que a função está configurada ou que atende ao caso do usuário.
