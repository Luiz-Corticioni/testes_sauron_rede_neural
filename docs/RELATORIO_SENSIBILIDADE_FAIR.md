# Sensibilidade de uma premissa FAIR em 30 dias

## O que foi acrescentado

Na ficha de uma análise FAIR, a opção **Examinar sensibilidade de uma premissa** executa o cenário original e duas variantes. Em cada variante, somente o fator escolhido é fixado no mínimo ou no máximo da faixa já declarada. Os demais mantêm suas distribuições originais. É possível escolher frequência, fatores aplicáveis ao modo ou o valor de uma parcela de perda.

Os resultados são médias simuladas no horizonte de 30 dias; a interface mostra as fontes e a qualidade declaradas no cenário. Não há alteração ou gravação de premissas nem de resultados. A execução exige as permissões de leitura financeira e utiliza a trava de simulações, com 100 a 3.000 sorteios por alternativa.

## Interpretação e limites

O cálculo mostra como essas duas escolhas extremas afetam a média sob o modelo informado. Não demonstra causalidade, não analisa todas as combinações, não mede interações nem calcula formalmente o valor da informação. A mesma semente ajuda na reprodução, mas não garante sorteios pareados quando o número de eventos muda. Diferenças incluem variação amostral; faixas mal fundamentadas não se tornam confiáveis por terem sido simuladas. Se mínimo e máximo forem iguais, não há variação dessa entrada.

Este recurso pode apoiar uma conversa sobre quais premissas investigar, mas não recomenda automaticamente coletar dados nem calcula quanto uma informação vale. A decisão depende do contexto, do custo de investigação e das alternativas existentes.

## Teste

Crie uma análise FAIR com faixas não constantes; na ficha, abra **Examinar sensibilidade de uma premissa**, escolha a frequência ou uma parcela de perda e compare os extremos com a simulação original. Os testes automatizados cobrem limites, repetibilidade, ausência de alteração do cenário e permissão. A suíte completa passou com 532 testes Django e Ruff aprovou o código. A análise de sensibilidade por premissa é inspirada em métodos gerais documentados pelo [NIST](https://www.itl.nist.gov/div898/handbook/pri/section2/pri212.htm), sem afirmar conformidade ou validação empírica do modelo.
