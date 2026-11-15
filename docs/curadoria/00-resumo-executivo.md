# Curadoria de segurança — resumo executivo

**Base:** Sauron `sprint5-conformidade`, commit `9774058`; pesquisa em 14/11/2026. Leitura de código próprio e fontes públicas, sem executar código externo ou alterar a aplicação. [Diagnóstico](01-sauron-diagnostico.md) · [20 projetos e métricas](02-longlist-e-criterios.md) · [9 análises](03-analise-por-solucao.md) · [SOC](04-visao-soc.md) · [Matriz](05-matriz-comparativa.md) · [Roadmap](06-roadmap-recomendacoes.md).

## Cinco conclusões

1. **FATO:** o Sauron relaciona ativos, vulnerabilidades e dependências e modela cenários financeiros de 30 dias; o próprio módulo afirma não ser FAIR completo ([diagnóstico](01-sauron-diagnostico.md), [modelo](../../inventario/matematica/montecarlo.py)). **INFERÊNCIA:** é um protótipo de priorização, não um SIEM/EDR empresarial comprovado.
2. **FATO:** [Wazuh documenta agentes e indexação](https://documentation.wazuh.com/current/getting-started/architecture.html) e [Greenbone descreve scanner e feeds](https://greenbone.github.io/docs/latest/background); a isca do Sauron aceita importação manual ([serviço](../../inventario/aplicacao/honeypot.py)). **INFERÊNCIA:** integrar dados dessas categorias é mais realista que recriar seus motores.
3. **FATO:** [Sigma documenta níveis, fontes e falsos positivos](https://sigmahq.io/sigma-specification/specification/sigma-rules-specification.html); [Cowrie documenta eventos e sessões](https://docs.cowrie.org/en/latest/OUTPUT.html). **INFERÊNCIA:** procedência, deduplicação e triagem humana devem anteceder automação de resposta. Taxas de falso positivo e ganhos de MTTD/MTTR **NÃO VERIFICADOS**.
4. **FATO:** [CI do commit-base](https://github.com/Luiz-Corticioni/testes_sauron_rede_neural/actions/runs/43473391539) passou nas validações de aplicação e reprovou o scan da imagem; o log registrou 47 itens HIGH. A tentativa anterior de `seed_demo --operacional` falhou em base isolada ([diagnóstico](01-sauron-diagnostico.md)). **INFERÊNCIA:** confiabilidade e análise do risco da própria plataforma vêm antes de ampliar escopo.
5. **FATO:** licenças variam: [regras Sigma usam DRL 1.1](https://github.com/SigmaHQ/sigma/blob/master/LICENSE), [Wazuh distingue componentes GPL/AGPL](https://github.com/wazuh/wazuh/blob/main/LICENSE) e [MISP é AGPL-3.0](https://github.com/MISP/MISP). **INFERÊNCIA:** comercialização, distribuição, feeds e serviços exigem revisão jurídica específica; licença copyleft não significa automaticamente proibição comercial.

## Cinco ações priorizadas

1. Corrigir seed operacional e testar rollback, autoria e rótulo de simulação.
2. Exibir origem, idade e indisponibilidade das fontes; não transformar dados ausentes em risco zero.
3. Analisar e tratar cada achado da imagem, mantendo o bloqueio do Trivy e registrando exceções justificadas.
4. Medir 100 sessões com Argon2 e limites reais do container; publicar capacidade e erros observados.
5. Projetar contrato de observação versionado e triagem humana; testar replay sanitizado antes de habilitar sensores reais.

A sequência, esforço, riscos, arquivos e critérios mensuráveis estão no [roadmap](06-roadmap-recomendacoes.md). Não habilitar scanner ativo, honeypot público ou APIs pagas sem autorização e validação.

**Limites:** Bitbucket foi pouco conclusivo; mantenedores ativos, adoção real, custos, conformidade e taxas de detecção das soluções não foram verificados. As comparações são documentais e não demonstram superioridade estatística de nenhum produto.
