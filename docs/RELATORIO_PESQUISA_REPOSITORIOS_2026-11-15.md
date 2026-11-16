# Pesquisa em repositórios e melhoria aplicada

## Melhoria implementada

A discussão do [Trivy sobre relatórios sem seção Results](https://github.com/aquasecurity/trivy/discussions/6487) mostra que a seção pode estar ausente em certas saídas. O importador do Sauron rejeitava tanto um relatório com lista vazia quanto outro sem essa seção. Agora ambos podem passar por prévia e confirmação, desde que tenham o formato e a data exigidos. O sistema informa explicitamente que nenhum achado reconhecido não comprova ausência de vulnerabilidades nem cobertura completa. Sete testes de scanner e demonstração passaram, incluindo relatório vazio, seção ausente e reimportação idempotente.

## Referências e decisões

- [CISA Vulnrichment](https://github.com/cisagov/vulnrichment) publica enriquecimentos de CVEs, incluindo pontos de decisão SSVC. O Sauron já possui avaliação SSVC; importar dados externos poderia ajudar em fase posterior, desde que se mantenham origem, versão da árvore, data e revisão local. Não é seguro presumir que a decisão da CISA substitui a avaliação da empresa.
- A [documentação de filtros do Trivy](https://github.com/aquasecurity/trivy/blob/main/docs/guide/configuration/filtering.md) diferencia situação de correção do fornecedor e severidade. Em etapa posterior, guardar esses campos declarados poderia facilitar triagem, mas `fixed` não deve encerrar automaticamente uma incidência: é necessário verificar versão, plataforma e aplicação efetiva da correção.
- O [OSV-Scanner](https://github.com/google/osv-scanner/blob/main/docs/offline-mode.md) oferece consulta offline a uma base local previamente obtida. Uma futura importação de resultados OSV pode ampliar a cobertura; adicionar automaticamente execução de scanner ou coleta em rede ultrapassaria o escopo atual e exigiria controles e testes próprios.

Essas referências não garantem completude nem correção dos dados recebidos. Nenhuma integração paga, varredura automática ou troca de tecnologia foi adicionada nesta etapa.
