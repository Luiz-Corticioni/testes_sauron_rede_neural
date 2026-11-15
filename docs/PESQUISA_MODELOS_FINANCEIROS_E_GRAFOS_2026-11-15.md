# Pesquisa: cenários financeiros, dados e grafos para o Sauron

Pesquisa em 15/11/2026 · [Documentação](README.md) · [Proposta anterior](PROPOSTA_MONTE_CARLO_CONTEXTO.md) · [Roadmap](curadoria/06-roadmap-recomendacoes.md)

## Escopo e método

Foram comparados documentação e páginas públicas de repositórios e bibliotecas com o código da branch `melhorias-curadoria`. As descrições dos projetos são dos próprios mantenedores; a utilidade para o Sauron e a ordem são julgamento técnico, não resultados de comparação experimental. Não foram instalados, executados, auditados ou submetidos à avaliação de desempenho os projetos externos. Licenças e manutenção podem mudar; antes de copiar código ou incluir uma dependência, verificar versão, licença integral, segurança, suporte e tamanho. Nenhum dado empresarial foi enviado a serviços externos.

## Ponto de partida concreto

- [Monte Carlo](../inventario/matematica/montecarlo.py) usa NumPy, PERT, uma variável de ocorrência por vínculo ativo/CVE, EPSS × fator hipotético de exposição, custos por C/I/A e máximo de perda por ativo, somando ativos. Também fornece média, percentis, excedência e comparação antes/depois com amostras comuns. Essas hipóteses não são uma estimativa calibrada da probabilidade de uma empresa ser atacada. O [serviço](../inventario/aplicacao/montecarlo.py) bloqueia o cálculo inteiro se qualquer vínculo elegível não possuir EPSS recente e coerente. KEV é exibido mas não altera numericamente a ocorrência.
- [Ativo](../inventario/models/ativos.py) já registra exposição, zona, portas e criticidade declarada; [relação tipada](../inventario/models/relacoes.py) registra rede, identidade e negócio com evidência, data e escopo. São declarações; não provam acessibilidade real nem permissões reais.
- [Risco](../inventario/matematica/risco.py) utiliza matrizes esparsas; [grafo de relações](../inventario/dominio/grafo_relacoes.py) calcula alcance e ciclos; [caminhos](../inventario/matematica/caminhos_ataque.py) têm custos relativos; [noisy-OR](../inventario/matematica/risco_noisy_or.py) é experimental e não integrado. Não converter pesos atuais, escores ou alcance diretamente em probabilidades.
- [Documentos](../inventario/models/documentos.py) já modelam SBOM, componente, achado e VEX com proveniência; não equivalem a scanner nem a prova de instalação. [Avaliação de previsão](../inventario/matematica/previsao_avaliacao.py) já contém Brier, calibração, PR-AUC e walk-forward. [Euler](../inventario/matematica/euler.py) oferece integração/derivação e EDO; [séries](../inventario/matematica/series.py) já mede risco-dia e tendência histórica.
- NumPy 2.3.5 e SciPy 1.18.1 já constam em `requirements.txt`; a decisão inicial deve aproveitar essa base em vez de acrescentar uma pilha de ML.

## Projetos examinados: o que aproveitar e o que não inferir

| Projeto e evidência primária | Ideia útil | Decisão para o Sauron |
|---|---|---|
| [QRALib](https://github.com/samlothen/QRALib) | Distribuições, eventos múltiplos, excedência, tornado, Morris e Sobol para análise quantitativa. | Usar como referência conceitual para separar frequência, impacto e sensibilidade. Página informa GPL-3.0: não copiar nem incorporar sem revisão de licença e distribuição. |
| [pyfair](https://github.com/Derive-Risk/pyfair) | Estrutura nós/fatores para análises FAIR e Monte Carlo. | Inspiração para decompor cenários e explicitar suposições; não declarar conformidade FAIR por usar nomes de fatores. A página informa MIT; compatibilidade e manutenção precisam ser revistas antes de adoção. |
| [SALib](https://github.com/SALib/SALib) | Morris, Sobol e métodos de sensibilidade globais. | Primeiro implementar análise de sensibilidade limitada com NumPy/SciPy existente. SALib é alternativa futura se custos, pressupostos e licença forem avaliados. Índices clássicos de Sobol exigem tratamento apropriado de dependência entre entradas. |
| [PyPortfolioOpt](https://github.com/PyPortfolio/PyPortfolioOpt) | Covariância, restrições e otimização de portfólio de investimentos. | Inspirar comparação de conjuntos de controles sob orçamento; não aplicar fronteira eficiente, retornos financeiros ou diversificação de ações como se fossem perdas cibernéticas. |
| [QuantStats](https://github.com/ranaroussi/quantstats) | Relatórios e visualizações de desempenho de portfólio. | Inspirar relatório executivo legível; Sharpe, drawdown e retornos não são métricas automáticas de incidentes. Não instalar para produzir poucos indicadores existentes. |
| [NumPy](https://github.com/numpy/numpy) e [SciPy](https://github.com/scipy/scipy) | Vetorização, amostragem, estatística, matrizes esparsas e otimização. | Já instalados: priorizar e medir CPU/memória. Registrar versões, semente e método; testes reproduzíveis não prometem sequências idênticas entre todas as versões. |
| [NetworkX](https://github.com/networkx/networkx) | Algoritmos de grafos e análise estrutural. | Usar como referência e eventual oráculo em testes; Sauron já tem BFS/ciclos. Só adicionar dependência se benchmark e necessidade mostrarem ganho. |
| [pandas](https://github.com/pandas-dev/pandas) e [Pandera](https://github.com/unionai-oss/pandera) | Tratamento tabular e validação explícita de esquemas. | Django/forms já validam entradas pequenas. Considerar ambos para lotes reais quando tamanho e complexidade justificarem; não carregar pandas só para um formulário. |
| [scikit-learn](https://github.com/scikit-learn/scikit-learn) | Modelos, pipelines e [calibração](https://scikit-learn.org/stable/modules/calibration.html). | Apenas experimento offline posterior, com dados rotulados e avaliação temporal; biblioteca não torna dados representativos nem converte escore em probabilidade confiável automaticamente. |
| [PyMC](https://github.com/pymc-devs/pymc) | Modelagem probabilística bayesiana e inferência. | Estudar depois que houver questão específica, dados, suporte operacional e comparação com modelo simples; evitar peso e tempo de inferência para o protótipo atual. |
| [OSV-Scanner](https://github.com/google/osv-scanner) e [Grype](https://github.com/anchore/grype) | Associação de componentes e vulnerabilidades a partir de pacotes/SBOMs e relatórios. | Considerar importação offline, validada e revisável de um formato de relatório; não executar scanner ou enviar dados para fora automaticamente. A associação é achado, não comprovação de exploração. OSV informa quais metadados podem ser enviados por suas integrações e oferece modo offline. |
| [CERT/CC SSVC](https://github.com/CERTCC/SSVC) | Priorização contextual por árvore de decisão. | Complementar a triagem já existente; não transformar categoria SSVC em probabilidade ou custo sem estudo próprio. |
| [dynamic_cyber_risk](https://github.com/alan-turing-institute/dynamic_cyber_risk) | Referência de pesquisa em risco cibernético dinâmico. | Somente leitura crítica; o repositório está arquivado e não foi validado como componente de produção. Não copiar horizontes anuais para o modelo de 30 dias. |

## Contrato proposto: um cenário compreensível

Exemplo fictício: **interrupção do faturamento por comprometimento de conta privilegiada**. O formulário deve pedir serviço, escopo, horizonte 30 dias e responsável. Para cada dado: valor ou faixa, unidade, fonte, data, autor e qualidade (medido, estimado, desconhecido). Sugestões:

| Grupo | Exemplo de entrada | Destino no modelo | Regra de interpretação |
|---|---|---|---|
| Financeiro | custo incremental de interrupção em R$/hora; faixa de gastos externos | magnitude da perda | Não somar receita bruta a lucro perdido nem contar despesas fixas duas vezes. |
| Operação | faixa de horas de indisponibilidade, restauração e pessoas afetadas | duração e custo incremental | Total de empregados não significa todos parados. Estabelecer se restauração já está incluída. |
| Contas e controles | quantidade agregada de contas privilegiadas, MFA, backup testado | descrição/evidência e, se fundamentado, parâmetros condicionais | Não converter automaticamente existência de MFA ou treinamento em eficácia percentual. Não armazenar senhas; proteger dados de identidade. |
| Superfície e CVEs | ativos, exposição, CVSS, EPSS, KEV, relação de rede | seleção e contexto do cenário | EPSS/KEV/SSVC não são probabilidade local de perda; não somar automaticamente sinais redundantes. |
| Integração | dependências de negócio, serviço e terceiro; alternativa e capacidade | serviços afetados e correlação de cenário | Relação ausente = desconhecida; fornecedor comum pode afetar vários sistemas simultaneamente. |
| Software | pacote e versão, PURL, SBOM e VEX | evidência de componente/achado revisável | Linguagem isolada não gera risco numérico nem prova vulnerabilidade. |

Exemplo aritmético, não resultado da aplicação: num sorteio hipotético em que há interrupção, 8 horas × R$ 5.000/h mais R$ 15.000 de despesas adicionais = R$ 55.000, desde que despesas não estejam incluídas no custo por hora. A simulação deve conter também sorteios sem evento; duração e valores são premissas da empresa fictícia.

## Núcleo matemático proposto

**Primeiro cenário, versão nova:** analista informa frequência ou probabilidade por janela de 30 dias e distribuição de impacto justificadas; não obter probabilidade empresarial pela multiplicação de EPSS e pesos arbitrários. Se escolher Bernoulli, máximo de um evento por cenário/30 dias deve estar explícito; para múltiplos eventos é necessária distribuição de contagem justificada, p. ex. Poisson somente sob suas hipóteses. Em cada execução, sortear ocorrência(s), duração e custos, somando uma única vez cada perda de negócio. Dados de empresa ou de consultor são estimativas até serem validados.

**Amostras e precisão numérica:** NumPy `Generator` com semente e algoritmo, versão do modelo e dependências, IDs ordenados e amostras comuns para o comparativo; limites de tempo, memória e trabalho. Testar sensibilidade à quantidade de simulações e a sementes diferentes; apresentar incerteza numérica separada da incerteza dos parâmetros. Quase-Monte Carlo [SciPy qmc](https://docs.scipy.org/doc/scipy/reference/stats.qmc.html) é hipótese de estudo, não promessa de convergência melhor em qualquer modelo discreto/de cauda.

**Resultados:** distribuição de perdas em R$ para 30 dias, média, mediana, P90/P95, chance simulada de exceder um limite, e perda média condicional ao evento. Se o cenário acontece em menos de 5% das iterações, o P95 incondicional pode ser zero mesmo havendo cauda de perdas; não ocultar esse fato. Análise de perda média acima do quantil exige definir a convenção para empates/massa no quantil. Percentis são condicionais às entradas, não garantias nem intervalo de confiança empírico.

**Sensibilidade e custo-benefício:** gráfico de faixas comparando, inicialmente, custo por hora, tempo de recuperação e frequência mediante variação isolada documentada; depois estudar interações com [SciPy Sobol](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.sobol_indices.html) ou SALib somente quando pressupostos e orçamento computacional forem respeitados. Comparar controle com e sem alteração, mesmo conjunto de amostras; exibir redução simulada, custo de implantação e incerteza. Ganhos de duas ações podem se sobrepor e não devem ser somados automaticamente.

**Grafo e álgebra linear:** mapear ativos e serviços por índice, relações tipadas para matriz CSR e vetores de custos e estado. Orientação é explícita: se A[i,j] representa serviço i depende do componente j, uma falha em j afeta i, sujeito à regra e evidência. BFS/CSR encontra dependências, ciclos e ponto único de falha sob o grafo declarado; não é caminho de ataque confirmado. Não multiplicar probabilidades independentes em ciclos ou múltiplos caminhos que compartilham causa. [SciPy csgraph](https://docs.scipy.org/doc/scipy/reference/sparse.csgraph.html) serve para avaliar algoritmos contra a implementação atual; evitar matriz densa e todos-os-pares, que pode explodir memória.

**Dependências comuns:** em cada iteração sortear uma causa compartilhada (p.ex. falha do fornecedor) uma vez e calcular os serviços afetados uma única vez; depois sorteios locais explicitamente condicionados se houver informação. Correntes relacionadas ou efeitos simultâneos exigem modelagem explícita. Cholesky/cópulas exigem correlação justificada, matriz simétrica semidefinida positiva e cuidado com distribuições marginais e caudas; adiar se não houver dados. Não usar a matriz de conectividade como matriz de correlação.

**Otimização de ações:** [SciPy milp](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html) pode futuramente selecionar ações binárias sob limite financeiro, horas e pré-requisitos. A função objetivo deve refletir efeito conjunto das ações, restrições reais e incerteza; somar ganhos marginais independentes pode superestimar economia. Começar comparando poucos conjuntos executáveis e testados, antes de declarar um plano ótimo.

## Geometria e Modo Euler: ideias úteis, com limites

1. **Plano custo × perda evitada:** cada medida é um ponto com intervalos e premissas; evidenciar medidas dominadas apenas quando horizontes e escopo forem iguais. Mostrar relação contextual, não recomendação automática.
2. **Matriz de exposição e cobertura:** ativos × controles com dados `sim/não/desconhecido`, por evidência e data. Cobertura é percentual apenas do perímetro observado; não implica eficácia ou conformidade.
3. **Distância entre perfis:** distância ou cosseno em vetores normalizados, com unidades, escalas e ausências explícitas. Útil para localizar ativos semelhantes e revisar dados; similaridade não é probabilidade de ataque. Não misturar valores em reais, contagens e EPSS sem normalização justificada.
4. **Séries e derivadas:** comparar tendência histórica com taxa de fechamento de pendências e intervalos de atualização. Risco-dia é unidade de escore × dia, não dinheiro. Lacunas e mudanças de escopo invalidam comparações diretas.
5. **Sistemas de equações e estabilidade:** exibir resíduos, número de condição e raio espectral já usados no módulo de risco. Solução matemática estável não valida causalidade ou pesos. EDO/SIS/SIR devem permanecer laboratório hipotético e não representar previsão de propagação real sem validação.
6. **Álgebra simbólica:** [SymPy](https://github.com/sympy/sympy) serve para estudo offline de derivadas e identidades; não adicionar ao fluxo web nem interpretar expressões arbitrárias de usuários sem revisão de segurança e limites de execução. O parser existente tem restrições que devem ser preservadas.

## ML: quando ajuda e quando não ajuda

Mais dados não garantem previsão. Só iniciar experimento com alvo, instante de previsão e janela de 30 dias definidos; dados históricos e rótulos completos e autorizados; correção para atrasos de descoberta e ausência de observação; separação temporal e por organização/ativo, evitando vazamento e repetição da mesma CVE em treino e teste. Comparar com linha de base simples, avaliar [calibração](https://scikit-learn.org/stable/modules/calibration.html), Brier, PR-AUC e falsos negativos no contexto de classe rara. A avaliação existente em `previsao_avaliacao.py` é ponto de partida, não modelo já treinado. Segregar identificação pessoal, registrar versão/deriva e exigir revisão humana. Sem dados suficientes, operar por cenários/intervalos e não usar rede neural.

## Implementação incremental sugerida

1. **Preparação:** testes do modelo atual, snapshot do contrato `30d-v1`, definir um único cenário fictício e revisão com especialista. Não alterar a saída ou chamadas existentes.
2. **Contexto e segurança:** modelos/formulários versionados para cenário, fonte, unidade, faixa e qualidade; permissões por função, validação, auditoria e migração. Ensaio: dados inexistentes, valores inválidos, autorização e migração reversível.
3. **Simulador 30d-v2 paralelo:** frequência e perdas informadas explicitamente; opcionalmente permitir cenário sem EPSS quando a origem da frequência estiver documentada. Dados ausentes continuam explícitos; não preencher zero. API/web/CLI sem quebrar v1; teste analítico de caso simples, não-negatividade, extremos, seed, comparativo monotônico quando aplicável, limites e ausência de dupla contagem.
4. **Painel:** curva de excedência, perda condicional, faixas, hipóteses, P95 contextualizado, custo de controle e qualidade dos dados. Testar acessibilidade, formato monetário, dados vazios e comparabilidade.
5. **Dependências e sensibilidade:** grafo de negócio com CSR e causa comum; testes de cadeia, ciclo, dependência compartilhada, relações ausentes/revogadas, deduplicação e escala. Depois sensibilidade limitada e testes de custo computacional.
6. **Somente após dados:** importação de relatório offline e experimentos de calibração/ML, com governança e revisão de licenças. Não ativar coleta externa ou scanner em rede por padrão, nem usar API paga da OpenAI.

**Critério de prontidão por fase:** testes de unidade/integração e permissões aprovados; relatório com dados fictícios, premissas, limitações, desempenho e rollback; documentação acessível; CI real verificada. Nenhuma técnica externa foi integrada por esta pesquisa.

## Referências para a interpretação

- [FIRST — EPSS](https://www.first.org/epss/): probabilidade de exploração observada da CVE em 30 dias, não probabilidade de perda de uma organização.
- [NIST SP 800-30 Rev. 1](https://csrc.nist.gov/pubs/sp/800/30/r1/final): cenário, ameaça, vulnerabilidade, probabilidade, impacto e incerteza.
- [FAIR Institute — fontes de dados](https://www.fairinstitute.org/hubfs/FAIR%20CRM%20Body%20of%20Knowledge/FAIR%20Institute%20--%20Analysts%20Guide%20to%20Cyber%20Risk%20Data%20Sources%20%28May%202025%29.pdf): dados medidos, estimados e derivados; frequência e magnitude.
- [scikit-learn — prevenção de vazamento](https://scikit-learn.org/stable/common_pitfalls.html) e [divisão temporal](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html).
