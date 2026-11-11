# Risco financeiro: proposta e primeira entrega — 11/11/2026

[Voltar ao README](../README.md) · [Manual de uso e perda financeira](GUIA_DE_USO.md#5-priorize-e-explore-cenários)

## Decisão e limite do modelo atual

O público executivo precisa comparar cenários em reais e entender a qualidade das premissas. Um número visualmente atraente não é uma medição confiável apenas por ter sido produzido por Monte Carlo. A tela existente simula 30 dias: usa EPSS multiplicado por um fator informado, pesos de impacto derivados de CVSS, eventos independentes por vínculo, maior perda por ativo e soma entre ativos. Custos iniciais são didáticos. Essas regras são escolhas do protótipo; não estabelecem chance de comprometimento da empresa, não estimam automaticamente prejuízo real e não constituem FAIR completo. A saída não deve ser apresentada como probabilidade calibrada ou valor financeiro auditado.

EPSS estima exploração observada de uma CVE na população mundial durante os próximos 30 dias; não conhece os ativos, a exposição, a efetividade dos controles ou os custos do cliente. Não se deve usar EPSS como probabilidade de ataque contra a empresa nem inferir que uma multiplicação arbitrária de fatores forneça uma probabilidade local. É um sinal de inteligência, com data e fonte, para apoiar identificação e priorização de cenários. KEV indica exploração conhecida, sem fornecer uma probabilidade local. Fonte: [FIRST — perguntas frequentes EPSS](https://www.first.org/epss/faq) e [FIRST — uso do EPSS](https://www.first.org/epss/using-epss).

## Entregue nesta fase

- Resumo executivo com média, percentil 95, frequência de perda **na simulação** e diferença média simulada após correções selecionadas; resultados são explicitamente hipotéticos e ficam indisponíveis quando o cálculo não puder ser feito.
- Calculadora opcional de custo de interrupção por incidente: `horas × perda econômica por hora + recuperação adicional`, aplicada a mínimo, valor mais provável e máximo das horas. O usuário pode transferir explicitamente essa faixa para o custo de disponibilidade por incidente de impacto alto. Horas e componentes não são enviados; a faixa aplicada é enviada à API para calcular e pode permanecer no cache do servidor. A simulação continua usando seus próprios pesos CVSS e demais hipóteses.
- O valor por hora precisa representar perda econômica incremental evitável, não faturamento bruto automaticamente. A recuperação não deve duplicar custo por hora, confidencialidade, integridade ou custos compartilhados. A fórmula linear é uma simplificação: sazonalidade, recuperação gradual, penalidades e capacidade ociosa podem invalidá-la. A faixa obtida não transforma o EPSS em probabilidade local nem comprova que o custo vale para todos os ativos.

## Dados a levantar com a organização

1. **Cenário e escopo:** serviço, ativo, proprietário, ameaça, via de acesso, condições de perda, dependências e horizonte de 30 dias. Exemplo: indisponibilidade do serviço de vendas após comprometimento de servidor exposto.
2. **Frequência e exposição:** janela de observação, eventos confirmados e definição consistente de tentativa e perda; alcance real, presença de CVE no ativo e evidências dos controles. Diferenciar tentativas, exploração, comprometimento e perda. Não tratar contagem de alertas como incidentes independentes.
3. **Magnitude:** duração de indisponibilidade e perda incremental por hora; custos extras de resposta e recuperação; impactos de confidencialidade, integridade e terceiros quando fundamentados. Distinguir receitas adiadas de perdas definitivas, registrar unidades e evitar sobreposição entre categorias, ativos e cenários.
4. **Qualidade:** para cada entrada, registrar fonte, responsável, data, período, unidade, método, intervalo de incerteza e situação (medido, estimado por especialista ou desconhecido). Evidência inexistente não deve virar zero. Usar dados sintéticos em demonstrações e limitar acesso a informações comerciais reais.

Para incidentes semelhantes, históricos internos e dados externos comparáveis podem apoiar intervalos, desde que sejam compatíveis em escopo, setor e período. A análise requer validação com responsáveis financeiro, operacional e de segurança. O [guia de fontes do FAIR Institute](https://www.fairinstitute.org/hubfs/FAIR%20CRM%20Body%20of%20Knowledge/FAIR%20Institute%20--%20Analysts%20Guide%20to%20Cyber%20Risk%20Data%20Sources%20%28May%202025%29.pdf) distingue frequência de eventos e magnitude das perdas e recomenda evidências e intervalos.

## Roteiro para uma empresa fictícia

Para uma apresentação, considere a **Loja Aurora**, organização inventada que depende de um portal de vendas. O cenário é a interrupção desse serviço em um incidente hipotético. Os dados abaixo foram escolhidos somente para explicar o cálculo; não são valores observados nem servem para estimar uma empresa real:

| Entrada fictícia | Valor |
|---|---:|
| Perda econômica incremental por hora parada | R$ 1.000 |
| Recuperação adicional, sem duplicar o custo por hora | R$ 2.000 por incidente |
| Duração mínima, mais provável e máxima | 4, 8 e 24 horas |
| Custo calculado mínimo, mais provável e máximo | R$ 6.000, R$ 10.000 e R$ 26.000 |

Na tela **Perda financeira**, preencha os cinco campos da calculadora com esses valores, escolha **Estimar custo por incidente** e confira a faixa. **Usar a faixa em disponibilidade** é opcional e altera a simulação da página atual; os valores de confidencialidade, integridade e exposição continuam sendo hipóteses separadas que devem ser explicadas. Não associe automaticamente esses custos a todos os ativos de uma organização real.

Para demonstrar a simulação, use um inventário de teste com incidências e observações EPSS válidas. O comando `seed_demo` pode criar um inventário fictício em banco vazio, mas não garante EPSS atualizado; para apresentar os valores atuais, solicite a atualização FIRST na tela com uma conta autorizada e rede disponível. Se os dados estiverem ausentes ou desatualizados, mostre as pendências em vez de inventar um EPSS ou prometer um resultado. A Loja Aurora é apenas a narrativa de apresentação e não é criada automaticamente no banco pelo `seed_demo`.

## Próximas fases propostas

1. **Catálogo de cenários e evidências:** cadastrar o contexto acima, permissões, versão, responsável, data de validade e fonte de cada entrada. Mostrar completude e dados insuficientes antes de qualquer resultado financeiro. Implementar testes de isolamento por permissão e histórico.
2. **Modelo econômico por cenário:** separar distribuição de frequência de eventos com perda e distribuição de magnitude, com premissas explícitas e horizonte de 30 dias. Aceitar faixas fundamentadas ou dados observados; não inferir frequência local a partir do EPSS. Se usar Poisson, declarar e validar suas condições; não usá-lo como verdade padrão. Tratar dependências e eventos que afetam múltiplos ativos para evitar soma indevida.
3. **Comparação de decisões:** registrar cenários de referência e intervenção, data, custo de implementação e fontes; comparar a mesma definição de evento e horizonte. Diferenças de média serão apresentadas como redução modelada condicionada às premissas; retorno financeiro só com custos e período compatíveis. Percentis descrevem o modelo, não intervalos de confiança estatística.
4. **Qualidade e validação:** sensibilidade às premissas, cenários pessimista/base/otimista identificados como escolhas, análise de convergência, revisão e backtesting quando houver dados, testes de propriedades e auditoria das mudanças. Com dados insuficientes, mostrar apenas contexto e lacunas.
5. **Revisão de método:** só usar a denominação FAIR para o que tiver escopo e fatores efetivamente implementados e revisados; manter claramente identificados qualquer aproximação e desvio. O horizonte segue sendo 30 dias: não anualizar EPSS ou perdas simplesmente multiplicando por 12.

## Verificação desta fase

A alteração não cria uma nova fonte de probabilidades nem muda a matemática da simulação. O resumo mostra resultados já retornados pela API; a calculadora produz uma sugestão local e só altera o formulário depois de ação explícita. Passaram 18 testes Django de integração e matemática, incluindo acesso e API. Um teste JavaScript executou os eventos reais com DOM simulado e verificou aritmética, aplicação, invalidação, limites, resumo, inventário vazio e EPSS ausente. Também passaram a verificação sintática JavaScript e o Ruff. Não houve teste visual em navegador real nesta fase. A execução do modelo depende das premissas e dados disponíveis no ambiente do usuário.
