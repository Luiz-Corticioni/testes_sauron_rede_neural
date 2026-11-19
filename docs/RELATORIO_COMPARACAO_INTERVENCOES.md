# Comparação de intervenção em análises FAIR

## O que mudou e por quê

Na tela de comparação de análises FAIR, o usuário pode descrever opcionalmente uma intervenção e declarar um custo incremental previsto para os mesmos 30 dias. Para incluí-lo na conta, o formulário exige origem e justificativa, além da confirmação de que o custo não está incluído nas parcelas dos cenários. A interface exibe a diferença entre perdas médias simuladas menos esse custo declarado, inclusive quando negativa. Um custo zero é distinto de custo desconhecido.

A comparação mantém a exigência de duas análises para o mesmo ativo, evento, ameaça, efeito, escopo e versão. Ela não altera as premissas nem inventa a eficácia de um controle. Os usuários precisam formular as hipóteses de ambos os cenários. As simulações são independentes: a diferença inclui variação amostral e não é intervalo de confiança, lucro, ROI, economia comprovada ou recomendação automática. O custo posterior aos 30 dias não integra o resultado.

## Limites e teste

A descrição e o custo são temporários nesta tela; não criam cadastro de intervenção nem são guardados na auditoria ou nas execuções. A confirmação contra dupla contagem é uma declaração do usuário, não uma verificação automática. A comparação continua vinculada a um ativo, não a um serviço de negócio inteiro; custos, eficácia e prazos não são inferidos do inventário.

Para testar, crie duas análises compatíveis, abra **Comparar análises**, informe intervenção, custo e fonte, e confirme que o custo é distinto das parcelas. Verifique o caso sem custo e a rejeição quando a confirmação falta. `tests.test_fair_fluxo` cobre os casos de custo ausente, zero, custo superior à diferença e cálculo aritmético. A suíte completa passou com 530 testes Django; Ruff também passou.

Referência: [FAIR Institute — guia de fontes para análise de risco](https://www.fairinstitute.org/hubfs/FAIR%20CRM%20Body%20of%20Knowledge/FAIR%20Institute%20--%20Analysts%20Guide%20to%20Cyber%20Risk%20Data%20Sources%20%28May%202025%29.pdf). O recurso não declara conformidade FAIR.
