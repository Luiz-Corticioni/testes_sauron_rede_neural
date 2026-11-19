# Análise por fatores FAIR em 30 dias

[Documentação](README.md) · [Motor e hipóteses](RELATORIO_FAIR_MOTOR_2026-11-16.md) · [Comparação](RELATORIO_FAIR_COMPARACAO_2026-11-16.md) · [Registros](RELATORIO_FAIR_REGISTRO_2026-11-16.md) · [Cobertura e limitações](MATRIZ_FAIR_30_DIAS.md)

## Qual pergunta o cenário responde?

Escolha um ativo, um evento de perda, uma ameaça ou causa e o escopo. Exemplo fictício: “interrupção do faturamento por falha operacional na unidade de demonstração”. Descreva o que está incluído e o que está fora da análise. Uma CVE, uma ferramenta ausente ou uma nota CVSS isolada não define toda a situação.

O modelo separa frequência de eventos de perda e magnitude financeira. A janela do Sauron é de **30 dias**. Os resultados dependem de premissas e não são previsão garantida, análise jurídica ou certificação FAIR. EPSS descreve exploração de uma CVE e não é convertido em chance de perda da empresa. Dados financeiros e fontes devem ser protegidos como informações sensíveis.

## Experimente com dados fictícios

1. Entre com conta autorizada e conclua o segundo fator. Abra **Perda financeira → Abrir cenários de negócio contextualizados → Analisar fatores FAIR**.
2. Escolha **Experimentar dados fictícios**. O formulário é preenchido com uma hipótese didática; nenhum dado é salvo nessa etapa. Selecione um ativo de demonstração e confira o evento e o escopo.
3. O exemplo parte de frequência de ameaças (TEF) e suscetibilidade. Na frequência, os números `0,1 / 0,5 / 1` representam limites e moda de uma hipótese para a taxa média em 30 dias, não porcentagens. Para suscetibilidade, `0,1 / 0,3 / 0,5` são proporções de 0 a 1 por ameaça. Os números são inventados e não devem ser usados para representar um cliente real.
4. Na primeira parcela, produtividade é tratada como perda primária; a faixa `1.000 / 5.000 / 10.000` reais é por evento de perda, não por mês de faturamento. Na primária, chances em branco significam que a parcela ocorre em todo evento; para representar uma chance menor, informe três valores entre 0 e 1. Se houver parcelas secundárias, informe a chance comum de efeito secundário por evento (SLEF); em cada parcela secundária, informe também três chances condicionadas à ocorrência desse efeito.
5. Leia as fontes, confirme que as parcelas não se sobrepõem e cabem no período, e registre. A confirmação é uma declaração: o sistema não consegue provar que as despesas sejam diferentes.
6. Na tela do cenário, escolha quantidade e semente e clique em **Calcular simulação**. Para preservar o resultado, marque a opção de guardar; pessoas com permissão de leitura podem simular sem guardar. Um registro guardado pode ser baixado em JSON e exige proteção da cópia.

## Como escolher os fatores

O formulário oferece cinco vias, de acordo com a informação disponível:

| Via | Frequência informada | Demais entradas necessárias |
|---|---|---|
| LEF | Taxa média de eventos de perda em 30 dias | Nenhuma decomposição de ameaça |
| TEF | Taxa média de eventos de ameaça em 30 dias | Suscetibilidade por ameaça |
| TEF com capacidade | Taxa média de eventos de ameaça em 30 dias | Capacidade e resistência |
| Contato com suscetibilidade | Taxa média de contatos em 30 dias | Probabilidade de ação e suscetibilidade |
| Contato decomposto | Taxa média de contatos em 30 dias | Probabilidade de ação, capacidade e resistência |

Escolha a via que suas fontes sustentam; não preencha fatores de outras vias. Capacidade e resistência são grandezas relativas à população de ameaças definida pelo cenário, não a porcentagem de máquinas com antivírus. Uma capacidade sorteada deve superar a resistência sorteada para gerar perda; empates não contam como superação.

As seis formas de perda podem ser classificadas como primárias ou secundárias conforme o contexto: produtividade, resposta, substituição, vantagem competitiva, multas ou decisões, e reputação. A perda secundária depende de reação de terceiros após o evento. Na versão 2, SLEF representa a chance da reação comum por evento de perda; a chance de cada parcela secundária é condicionada à reação. As parcelas de um mesmo evento compartilham a reação, mas seus sorteios de ocorrência e magnitude são independentes depois dela. Não some a mesma despesa em parcelas diferentes nem inclua valores fora do período. A mesma combinação de tipo e categoria é aceita uma vez por cenário.

## Como interpretar

- **Frequência média de eventos de perda:** média dos eventos sorteados por janela. Uma janela pode conter mais de um evento.
- **Janelas com evento:** proporção das simulações que tiveram ao menos um evento de perda. Um evento pode ter valor financeiro zero.
- **Perda média e P95:** média e percentil da amostra simulada; P95 não é perda máxima nem intervalo de confiança. Com eventos raros, o P95 pode ser zero mesmo quando uma perda grande é possível.
- **Excedência:** proporção de simulações cuja perda foi estritamente maior que cada valor mostrado.

As faixas determinam uma distribuição beta-PERT; taxas determinam contagens Poisson. Além da reação comum às parcelas secundárias de um evento, o modelo assume independência entre os fatores especificados no [relatório do motor](RELATORIO_FAIR_MOTOR_2026-11-16.md) e no [relatório da versão 2](RELATORIO_FAIR_SLEF_2026-11-16.md). Não pressupõe que essas distribuições sejam exigidas pelo FAIR. Não modela dependências temporais, pagamentos posteriores aos 30 dias ou calibração automática. Se essas hipóteses não forem adequadas, não use os números como evidência de precisão.

## Compare e guarde

Em **Comparar com outra análise**, use **Criar alternativa a partir desta análise**. O formulário copia os dados para revisão, mas não altera o original nem salva automaticamente. Modifique os fatores que pretende avaliar, atualize suas fontes e confirme novamente a declaração de custos. O sistema só compara registros com mesmo ativo, evento, ameaça, efeito, escopo e versão.

A comparação usa amostras independentes: a diferença entre médias inclui variação amostral. Não é economia comprovada nem retorno de investimento; o custo de uma medida precisa ser analisado separadamente. Análises antigas da versão 1 continuam calculáveis com suas hipóteses originais; uma cópia usa a versão 2 e só pode ser comparada com outra análise da versão 2. As execuções guardadas incluem versão do modelo, semente, quantidade, premissas, resultado e versões do ambiente. Semente e versões ajudam na reprodução, mas não garantem igualdade em versões futuras ou arquiteturas distintas.

Na comparação, é possível informar uma intervenção e, opcionalmente, seu custo adicional estimado nos mesmos 30 dias. Para subtrair o custo, informe sua fonte e confirme que ele não aparece nas parcelas das duas análises. O resultado é uma diferença entre médias simuladas menos o custo declarado: não comprova eficácia, lucro ou retorno. A intervenção e o custo são temporários e não ficam gravados; consulte [o relatório](RELATORIO_COMPARACAO_INTERVENCOES.md).

Na ficha de uma análise, **Examinar sensibilidade de uma premissa** compara os extremos de uma faixa já informada. A análise varia um fator por vez e não mede causalidade nem calcula valor da informação. Os resultados são temporários. Consulte [sensibilidade FAIR](RELATORIO_SENSIBILIDADE_FAIR.md).
