# Relatório — sensibilidade das premissas financeiras

[Guia de cenários](CENARIOS_FINANCEIROS.md)

## Mudança

Foi adicionada uma tela que compara faixas de probabilidade de ocorrência, custo incremental por hora e custo adicional do cenário de 30 dias. A pessoa responsável informa mínimo, máximo e justificativa; nenhuma faixa é inventada pela aplicação. As entradas não são salvas nem alteram o cenário original. Cada alternativa varia somente um fator e utiliza a mesma semente, mantendo os sorteios comparáveis. O limite é 20.000 simulações por alternativa, sob a trava existente.

## Verificação e interpretação

Testes cobrem resultado analítico para custo fixo e probabilidades zero/um, repetibilidade, médias na escala correta, recusa de faixas fora do valor original ou inválidas, limite de carga, formulário, permissões e MFA. Os valores mostram a sensibilidade à hipótese escolhida; não medem causalidade, interações entre fatores nem precisão do modelo. O EPSS não é usado como probabilidade local.
