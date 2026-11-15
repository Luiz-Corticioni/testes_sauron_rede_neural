# Cenários financeiros contextualizados — primeira etapa

[Documentação](README.md) · [Pesquisa e fases](PESQUISA_MODELOS_FINANCEIROS_E_GRAFOS_2026-11-15.md)

A interface **Monte Carlo → Abrir cenários de negócio contextualizados** permite registrar cenários de interrupção e simular uma hipótese de perda em 30 dias, sem substituir o modelo anterior por CVE. Na primeira etapa, gerente com permissões de leitura e inclusão pode criar; leitura e simulação exigem permissão específica, sessão e MFA. Operadores e auditores não recebem acesso por padrão; o cadastro gera auditoria sem registrar valores financeiros nela. Dados financeiros no banco são sensíveis e seguem as mesmas necessidades de proteção e backup da instalação.

## Exemplo fictício

Crie um ativo demonstrativo de faturamento e registre interrupção com probabilidade hipotética 0,1 (10% em 30 dias), duração 4/8/24 horas, custo incremental de R$ 1.000/h e adicional de R$ 2.000. Marque qualidade **fictício ou demonstrativo**, informe a origem e a data. Esses números são exemplos inventados. Opcionalmente descreva um controle e forneça outra probabilidade hipotética, sem pressupor eficácia. Quantidades de pessoas e contas privilegiadas são contexto, não viram multiplicadores automáticos. Para novas premissas, registre outro cenário; esta primeira etapa não oferece edição/exclusão nem retenção automática.

O simulador usa até uma ocorrência por janela, probabilidade informada, duração PERT e custos por hora/adicional fixos. Assume que o início, condicionado à ocorrência, é uniforme dentro da janela de 720 horas e conta apenas as horas de interrupção até o fim dos 30 dias; o custo adicional é atribuído no início. Usa as mesmas amostras na comparação e informa quando nenhum evento ocorreu. Um P95 zero pode coexistir com perdas grandes em poucos cenários. As proporções e percentis descrevem o modelo e suas entradas, não uma chance medida, previsão garantida ou FAIR completo. EPSS não é usado para atribuir probabilidade de perda local; não forneça EPSS como se fosse essa probabilidade.

Custo incremental por hora e custo adicional não devem repetir a mesma despesa. A origem, qualidade e data cadastradas se aplicam ao conjunto de premissas e não verificam automaticamente sua veracidade. A validação aceita 0 a 720 horas, mínimo < valor mais provável < máximo, valores financeiros não negativos, probabilidade entre 0 e 1 e comparação somente se controle e hipótese após controle forem informados. Quantidades ausentes permanecem desconhecidas, não são convertidas em zero.

## Limitações desta etapa

Este modelo cobre um ativo e um cenário. Não incorpora grafo, interdependências, múltiplos eventos, distribuições para custos, proveniência por parâmetro, comparação de custo da medida nem estimação por histórico. A diferença simulada não é economia comprovada e pode ser negativa. O formulário não garante que a origem descrita seja verdadeira. Não há treinamento de ML nem calibração local. Novas funcionalidades devem ser incorporadas em fases com testes e sem substituir o contrato anterior.

## Verificação da primeira etapa

A suíte completa executou 456 testes Django no Windows; testes direcionados verificaram extremos de probabilidade, cálculo condicional, limitação ao período, reprodutibilidade, comparação de controle, permissões, MFA, CSRF, auditoria e rollback. A imagem foi construída em container de teste separado, a migração 0031 aplicada e um cenário fictício foi criado e simulado. A primeira tentativa de teste direto por shell usou `float` para um campo decimal e foi rejeitada; com `Decimal`, tipo utilizado no tratamento do formulário, o cálculo foi concluído. O resultado não valida o modelo com dados reais.
