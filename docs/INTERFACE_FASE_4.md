# Interface — fase 4: teia de dependências

O mapa organiza os ativos por forças, preservando a direção dos vínculos e o cálculo existente. A biblioteca D3 e suas dependências são servidas localmente, com licenças incluídas; não há CDN ou chamada externa. O cálculo visual é limitado à janela existente de 60 ativos, com distribuição alternativa se a biblioteca não carregar.

Busca, filtros por tipo e maior CVSS, seleção de ativo, detalhes de incidências, ampliação e deslocamento ajudam a explorar a rede. A tabela continua disponível sem JavaScript. A cor representa o índice do modelo e o tamanho, a criticidade declarada: nenhum deles representa probabilidade de exploração. Linhas destacadas indicam caminhos possíveis a partir de ativos com CVSS conhecido de pelo menos 9, não um ataque observado.

As informações exibidas vêm de incidências abertas, em tratamento ou aceitas; são apresentados até três exemplos por ativo. A ausência de incidências no recorte não demonstra que o ativo seja seguro. A classificação do grafo é apenas visual e não altera as decisões do modelo de risco.

Verificações: 515 testes Django aprovados, testes de grafo com Node (incluindo a biblioteca local) e análise Ruff. A prévia foi inspecionada em navegador com dados de demonstração; zoom permite ampliar os rótulos em redes densas.
