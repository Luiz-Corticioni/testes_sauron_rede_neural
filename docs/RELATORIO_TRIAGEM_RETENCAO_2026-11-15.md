# Triagem de scanner e visibilidade de retenção

O detalhe de relatórios Trivy mostra contagens e filtros para achados sem revisão, aplicáveis, não aplicáveis e inconclusivos. A classificação é a revisão mais recente de cada achado; o histórico permanece acessível. Resultados são paginados em grupos de 25, e o link preserva o índice original mesmo após filtrar. Essas classificações são avaliações humanas e não alteram incidências automaticamente.

A tela da política de iscas informa quantos IPs e revisões já ultrapassaram o prazo configurado, apenas quando a conta tem as permissões de leitura dos dois tipos. O cálculo usa a política vigente, com padrão de 90 dias. A contagem não prova que o agendador esteja funcionando e não executa exclusão; backups e arquivos externos têm retenção própria. Também foi corrigida uma frase antiga da documentação que contradizia a rotina de retenção existente.

Passaram 13 testes de scanner e retenção, incluindo filtro pela última revisão, preservação do índice, prazo, negação de acesso e proteção das contagens. A capacidade da rotina depende de o agendador estar ativo e pode haver fila de lotes vencidos.
