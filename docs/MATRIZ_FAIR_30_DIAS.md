# Cobertura FAIR no Sauron

Referência: [FAIR Standard v3.0](https://www.fairinstitute.org/hubfs/Standards%20Artifacts/Factor%20Analysis%20of%20Information%20Risk%20%28FAIR%29%20Standard%20v3.0%20%28January%202025%29.pdf). O Sauron usa seus conceitos centrais, mas não passou por certificação ou auditoria de conformidade. O modelo tem horizonte de 30 dias por decisão do projeto.

| Conceito | Tratamento no Sauron |
| --- | --- |
| Cenário de risco | Ativo, evento, ameaça, efeito sobre o ativo e escopo; fontes, data e qualidade das estimativas. |
| Frequência de perda (LEF) | Informada diretamente ou calculada por frequência de ameaça e suscetibilidade. |
| Frequência de ameaça (TEF) | Informada diretamente ou decomposta em frequência de contato e probabilidade de ação. |
| Motivação da ameaça | Valor, esforço e risco percebidos podem ser registrados como contexto qualitativo; não são transformados automaticamente em probabilidades. |
| Suscetibilidade | Informada diretamente ou estimada pela comparação entre capacidade da ameaça e resistência. Habilidades e recursos podem ser documentados. |
| Magnitude e frequência de efeitos secundários | Parcelas primárias e secundárias com faixas e chances; na versão 2, uma reação secundária comum condiciona as parcelas secundárias. |
| Formas de perda | Produtividade, resposta, substituição, vantagem competitiva, multas e reputação, em parcelas primárias ou secundárias conforme o cenário. |
| Avaliação e decisão | Simulação com múltiplos eventos, média, percentis e curva de excedência; comparação de cenários equivalentes e registro opcional das premissas, resultado, semente e versões. |

As taxas por janela usam Poisson e as faixas usam beta-PERT, escolhas do Sauron e não exigências do padrão. A comparação usa simulações independentes: a diferença entre médias não é economia garantida. Além da reação secundária comum, dependências entre fatores e parcelas não são modeladas. As perdas são atribuídas à mesma janela de 30 dias; não há simulação explícita de pagamentos após esse período. A análise depende de dados e julgamento humanos, não de conversão automática de EPSS ou CVSS em risco financeiro. Não implementa toda a metodologia FAIR-CAM nem validação estatística automática das estimativas. Consulte o [guia de preenchimento](GUIA_FAIR_30_DIAS.md).
