# Cenários financeiros contextualizados — primeira etapa

[Documentação](README.md) · [Pesquisa e fases](PESQUISA_MODELOS_FINANCEIROS_E_GRAFOS_2026-11-15.md)

A interface **Monte Carlo → Abrir cenários de negócio contextualizados** permite registrar cenários de interrupção e simular uma hipótese de perda em 30 dias, sem substituir o modelo anterior por CVE. Na primeira etapa, gerente com permissões de leitura e inclusão pode criar; leitura e simulação exigem permissão específica, sessão e MFA. Operadores e auditores não recebem acesso por padrão; o cadastro gera auditoria sem registrar valores financeiros nela. Dados financeiros no banco são sensíveis e seguem as mesmas necessidades de proteção e backup da instalação.

## Exemplo fictício

Crie um ativo demonstrativo de faturamento e registre interrupção com probabilidade hipotética 0,1 (10% em 30 dias), duração 4/8/24 horas, custo incremental de R$ 1.000/h e adicional de R$ 2.000. Marque qualidade **fictício ou demonstrativo**, informe a origem e a data. Esses números são exemplos inventados. Opcionalmente descreva um controle e forneça outra probabilidade hipotética, sem pressupor eficácia. Quantidades de pessoas e contas privilegiadas são contexto, não viram multiplicadores automáticos. Para novas premissas, registre outro cenário; esta primeira etapa não oferece edição/exclusão nem retenção automática.

O simulador usa até uma ocorrência por janela, probabilidade informada, duração PERT e custos por hora/adicional fixos. Assume que o início, condicionado à ocorrência, é uniforme dentro da janela de 720 horas e conta apenas as horas de interrupção até o fim dos 30 dias; o custo adicional é atribuído no início. Usa as mesmas amostras na comparação e informa quando nenhum evento ocorreu. Um P95 zero pode coexistir com perdas grandes em poucos cenários. As proporções e percentis descrevem o modelo e suas entradas, não uma chance medida, previsão garantida ou FAIR completo. EPSS não é usado para atribuir probabilidade de perda local; não forneça EPSS como se fosse essa probabilidade.

Custo incremental por hora e custo adicional não devem repetir a mesma despesa. A origem, qualidade e data cadastradas se aplicam ao conjunto de premissas e não verificam automaticamente sua veracidade. A validação aceita 0 a 720 horas, mínimo < valor mais provável < máximo, valores financeiros não negativos, probabilidade entre 0 e 1 e comparação somente se controle e hipótese após controle forem informados. Quantidades ausentes permanecem desconhecidas, não são convertidas em zero.

## Limitações desta etapa

Este modelo calcula perdas para um ativo e um cenário. A consulta de relações é estrutural e não altera o cálculo individual. A opção separada de causa compartilhada aceita custos explicitamente informados para serviços dependentes; não inclui múltiplos eventos, distribuições para custos, proveniência por parâmetro, custo de implantação da medida nem estimação por histórico. A diferença simulada não é economia comprovada e pode ser negativa. O formulário não garante que a origem descrita seja verdadeira. Não há treinamento de ML nem calibração local. Novas funcionalidades devem ser incorporadas em fases com testes e sem substituir o contrato anterior.

## Verificação da primeira etapa

A suíte completa executou 456 testes Django no Windows; testes direcionados verificaram extremos de probabilidade, cálculo condicional, limitação ao período, reprodutibilidade, comparação de controle, permissões, MFA, CSRF, auditoria e rollback. A imagem foi construída em container de teste separado, a migração 0031 aplicada e um cenário fictício foi criado e simulado. A primeira tentativa de teste direto por shell usou `float` para um campo decimal e foi rejeitada; com `Decimal`, tipo utilizado no tratamento do formulário, o cálculo foi concluído. O resultado não valida o modelo com dados reais.

## Relações de negócio e sensibilidade

Na página do cenário, usuários com permissão de leitura de relações podem abrir **Analisar dependências** e informar o escopo exato cadastrado. O grafo utiliza a camada negócio e segue a direção declarada de fornecedor para consumidor, excluindo relações revogadas, vencidas, fora do perímetro ou com ativos inativos. Relações ausentes não provam isolamento; esta consulta não comprova propagação, nem muda os custos da simulação. São exibidos no máximo 20 consumidores e um identificador do recorte.

Após simular, a tela compara a média original com duas alternativas que fixam a duração, respectivamente, no mínimo e no máximo declarados. As três usam as mesmas ocorrências e horários sorteados; os custos e a probabilidade permanecem iguais. Isso mostra a sensibilidade dessa premissa, não é uma análise global nem validação dos valores. Se não houver evento sorteado, as três médias podem ser zero.

## Causa compartilhada entre serviços

Em um cenário, **Simular causa compartilhada** pede o escopo exato e até três serviços dependentes na interface. Informe para cada um custos incrementais por hora e adicionais, com justificativa, e confirme que não há sobreposição. O servidor rejeita serviços repetidos, a origem, relações vencidas ou não alcançáveis e recortes com mais de 100 serviços alcançáveis; o limite técnico é dez serviços. As entradas e resultados ficam apenas na requisição.

A hipótese é deliberadamente forte: quando a causa ocorre, todos os serviços escolhidos são afetados simultaneamente pela mesma duração sorteada. Um serviço é contado apenas uma vez mesmo que seja alcançado por caminhos paralelos ou ciclos. O grafo não fornece a probabilidade do evento: continua valendo a hipótese registrada no cenário. A soma presume que valores informados não se sobrepõem; a confirmação do usuário não prova que os custos estejam corretos. A comparação de controle altera apenas a probabilidade hipotética existente, sem estimar sua eficácia. O resultado registra o hash do recorte e relações excluídas; não representa distribuição conjunta calibrada ou incidentes independentes.

## Faixas de custo e probabilidade

Em **Analisar sensibilidade**, informe uma origem e ao menos uma faixa mínima/máxima para probabilidade, custo por hora ou custo adicional. Cada faixa deve conter o valor original. A análise varia uma premissa por vez e reutiliza a mesma semente para comparar a média base e as médias nos extremos; aceita até 20.000 sorteios por alternativa e compartilha o limite de concorrência das simulações. As faixas não são persistidas. Não é análise global, não trata a interação entre fatores e não calibra probabilidade de perda.
