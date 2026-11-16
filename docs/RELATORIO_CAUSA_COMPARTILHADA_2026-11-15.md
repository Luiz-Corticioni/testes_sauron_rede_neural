# Relatório — causa compartilhada em cenários financeiros

[Guia](CENARIOS_FINANCEIROS.md) · [Documentação](README.md)

## O que mudou e por quê

O cenário contextual ganhou uma simulação separada para reunir custos incrementais de serviços alcançáveis por relações de negócio em um escopo. O mesmo evento e a mesma duração afetam os serviços selecionados: esta hipótese visível permite estudar um ponto único de falha sem converter as arestas em probabilidades. É obrigatório informar custos, suas justificativas e confirmar que não se sobrepõem; a aplicação não tem como garantir que a declaração é verdadeira.

O serviço valida permissão de leitura financeira e de relações, escopo, atualidade das relações, membros ativos e alcance. Recortes truncados acima de 100 alcançáveis são recusados, em vez de calcular sobre uma lista incompleta. Cada serviço só pode aparecer uma vez, inclusive em grafos com ciclos e caminhos paralelos. A interface mostra três linhas; o limite no servidor é dez. Nenhuma premissa é salva e o inventário não muda. Custos somados têm limites de segurança, e o modelo é identificado como `sauron.interrupcao-compartilhada/30d-v1` com hash do recorte e semente.

## Testes e limites

Os testes verificam custo analítico de uma causa com dois serviços e múltiplos caminhos, ciclo, reprodução com semente, recusa de duplicatas, origem, serviço desconectado após revogação, ausência de confirmação, permissões e fluxo de formulário. O modelo não estima propagação automática, atraso diferencial, impactos por dependência ou dados observados. Valores em um formulário podem ser incoerentes ou duplicados economicamente mesmo quando o usuário declara o contrário.
