# Validação do percurso de decisão de segurança

## Evidência automatizada

O teste `tests.test_percurso_decisao` executa um percurso sintético com banco descartável: declara um perímetro e serviço, importa um resultado OSV fictício por prévia e confirmação, registra revisão inconclusiva, confere que não surgiu incidência automática, consulta a procedência e compara análises FAIR com custo declarado e sensibilidade. Utiliza o cliente de testes do Django e uma sessão com MFA preparada pela fixture; não executa varredura nem acessa um servidor SMTP ou fonte externa. A suíte completa passou com 537 testes Django, incluindo esse percurso, e Ruff passou.

Esse teste demonstra somente o comportamento coberto pelo cenário e não comprova utilidade para usuários reais, segurança integral, desempenho em produção nem implantação de rede. Análises FAIR continuam ligadas a ativos, não automaticamente ao serviço. O custo declarado na comparação é temporário; a análise de sensibilidade não calcula valor formal da informação.

## Roteiro para validação com pessoas

Com autorização da organização e em ambiente de demonstração separado, fornecer dados fictícios para pelo menos duas perspectivas: analista de segurança e responsável por um serviço de negócio. As pessoas devem executar as tarefas sem receber a resposta previamente:

1. Identificar o serviço de faturamento e seus ativos declarados.
2. Distinguir um achado sem revisão de uma incidência confirmada, localizando a origem e a data declarada.
3. Apontar que informações ainda precisam ser verificadas antes de decidir.
4. Comparar dois cenários de 30 dias e explicar o efeito do custo declarado.
5. Examinar a sensibilidade de uma premissa e explicar os limites do resultado.

Registrar, com a permissão dos participantes, o resultado de cada tarefa, dúvidas, erros de interpretação e o tempo observado. Usar critérios previamente definidos: conclusão sem ajuda, identificação correta de dados desconhecidos e ausência de interpretação da simulação como perda garantida. Tempo e satisfação só devem ser comparados depois de definir amostra, contexto, referência e método. Evitar coletar dados pessoais ou financeiros reais no primeiro ensaio.

## Estado

O percurso automatizado é uma validação sintética. Não houve entrevista, ensaio presencial, teste com cliente, estudo estatístico ou mensuração de ganho operacional nesta etapa. Não preencha resultados de participantes nem afirme benefícios antes de realizá-los.
