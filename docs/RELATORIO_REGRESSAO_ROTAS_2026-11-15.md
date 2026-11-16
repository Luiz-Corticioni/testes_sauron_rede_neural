# Correção do teste de rotas

A suíte completa identificou que o teste genérico de rotas nomeadas não fornecia o novo parâmetro inteiro `indice`, necessário para abrir a revisão de um achado. Foi incluído um índice de exemplo no gerador de argumentos do próprio teste, preservando a verificação de todas as rotas e a resposta 404 para relatório inexistente. A falha estava no teste de regressão, não significava que a revisão do achado fosse acessível sem índice.
